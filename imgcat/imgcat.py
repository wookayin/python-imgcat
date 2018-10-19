"""
imgcat in Python.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import base64
import sys
import os
import struct
import io
import re
import subprocess


IS_PY_2 = (sys.version_info[0] <= 2)
IS_PY_3 = (not IS_PY_2)

if IS_PY_2:
    FileNotFoundError = IOError  # pylint: disable=redefined-builtin


TMUX_WRAP_ST = b'\033Ptmux;'
TMUX_WRAP_ED = b'\033\\'

OSC = b'\033]'
CSI = b'\033['
ST  = b'\a'      # \a = ^G (bell)


def get_image_shape(buf):
    '''
    Extracts image shape as 2-tuple (width, height) from the content buffer.

    Supports GIF, PNG and other image types (e.g. JPEG) if imagemagick is installed.
    Returns (None, None) if it can't be identified.
    '''
    def _unpack(fmt, buffer, mode='Image'):
        try:
            return struct.unpack(fmt, buffer)
        except struct.error:
            raise ValueError("Invalid {} file".format(mode))

    # TODO: handle 'stream-like' data efficiently, not storing all the content into memory
    L = len(buf)

    if L >= 10 and buf[:6] in (b'GIF87a', b'GIF89a'):
        return _unpack("<hh", buf[6:10], mode='GIF')
    elif L >= 24 and buf.startswith(b'\211PNG\r\n\032\n') and buf[12:16] == b'IHDR':
        return _unpack(">LL", buf[16:24], mode='PNG')
    elif L >= 16 and buf.startswith(b'\211PNG\r\n\032\n'):
        return _unpack(">LL", buf[8:16], mode='PNG')
    else:
        # everything else: rely on imagemagick?
        try:
            p = subprocess.Popen(['identify', '-'],
                                 stdout=subprocess.PIPE, stdin=subprocess.PIPE)
            p.stdin.write(buf)
            identify = p.communicate()[0]
            p.stdin.close()

            re_m = re.search(r'(\d+)x(\d+)', identify.decode())
            if re_m:
                return int(re_m.group(1)), int(re_m.group(2))

        except FileNotFoundError:
            # imagemagick not available
            sys.stderr.write("Warning: cannot determine the image size; install imagemagick?\n")
            pass

        return None, None


def to_content_buf(data):
    # TODO: handle 'stream-like' data efficiently, rather than storing into RAM

    if isinstance(data, bytes):
        return data

    elif isinstance(data, io.BufferedReader) or \
            (IS_PY_2 and isinstance(data, file)):  # pylint: disable=undefined-variable
        buf = data
        return buf.read()

    elif isinstance(data, io.TextIOWrapper):
        return data.buffer.read()

    elif 'numpy' in sys.modules and isinstance(data, sys.modules['numpy'].ndarray):
        # numpy ndarray: convert to png
        im = data
        if len(im.shape) == 2:
            mode = 'L'     # 8-bit pixels, grayscale
            im = im.astype(sys.modules['numpy'].uint8)
        elif len(im.shape) == 3 and im.shape[2] in (3, 4):
            mode = None    # RGB/RGBA
        else:
            raise ValueError("Expected a 3D ndarray (RGB/RGBA image) or 2D (grayscale image), "
                             "but given shape: {}".format(im.shape))

        try:
            from PIL import Image
        except ImportError as e:
            raise ImportError(e.msg +
                              "\nTo draw numpy arrays, we require Pillow. " +
                              "(pip install Pillow)")       # TODO; reraise

        with io.BytesIO() as buf:
            Image.fromarray(im, mode=mode).save(buf, format='png')
            return buf.getvalue()

    elif 'PIL.Image' in sys.modules and isinstance(data, sys.modules['PIL.Image'].Image):
        # PIL/Pillow images
        img = data

        with io.BytesIO() as buf:
            img.save(buf, format='png')
            return buf.getvalue()

    elif 'matplotlib' in sys.modules and isinstance(data, sys.modules['matplotlib'].figure.Figure):
        # matplotlib figures
        fig = data
        if fig.canvas is None:
            from matplotlib.backends.backend_agg import FigureCanvasAgg
            FigureCanvasAgg(fig)

        with io.BytesIO() as buf:
            fig.savefig(buf)
            return buf.getvalue()

    else:
        raise TypeError("Unsupported type : {}".format(type(data)))


def get_tty_size():
    with open('/dev/tty') as tty:
        rows, columns = subprocess.check_output(['stty', 'size'], stdin=tty).split()
    return int(rows), int(columns)


def imgcat(data, filename=None,
           width=None, height=None, preserve_aspect_ratio=True,
           pixels_per_line=24,
           fp=None):
    '''
    Print image on terminal (iTerm2).

    Follows the file-transfer protocol of iTerm2 described at
    https://www.iterm2.com/documentation-images.html.

    Args:
        data: the content of image in buffer interface, numpy array, etc.
        width: the width for displaying image, in number of characters (columns)
        height: the height for displaying image, in number of lines (rows)
        fp: The buffer to write to, defaults sys.stdout
    '''
    if fp is None:
        fp = sys.stdout if IS_PY_2 \
            else sys.stdout.buffer  # for stdout, use buffer interface (py3)

    buf = to_content_buf(data)
    if len(buf) == 0:
        raise ValueError("Empty buffer")

    if height is None:
        im_width, im_height = get_image_shape(buf)
        if im_height:
            assert pixels_per_line > 0
            height = (im_height + (pixels_per_line - 1)) // pixels_per_line

            # automatically limit height to the current tty,
            # otherwise the image will be just erased
            tty_height, _ = get_tty_size()
            height = max(1, min(height, tty_height - 9))
        else:
            # image height unavailable, fallback?
            height = 10

    # need to detect tmux
    is_tmux = 'TMUX' in os.environ and 'tmux' in os.environ['TMUX']

    # tmux: print some margin and the DCS escape sequence for passthrough
    # In tmux mode, we need to first determine the number of actual lines
    if is_tmux:
        fp.write(b'\n' * height)
        # move the cursers back
        fp.write(CSI + b'?25l')
        fp.write(CSI + b"%dF" % height)
        fp.write(TMUX_WRAP_ST + b'\033')

    # now starts the iTerm2 file transfer protocol.
    fp.write(OSC)
    fp.write(b'1337;File=inline=1')
    fp.write(b';size=%d' % len(buf))
    if filename:
        fp.write(b';name=%s' % base64.b64encode(filename.encode()))
    fp.write(b';height=%d' % height)
    if width:
        fp.write(b';width=%d' % width)
    if not preserve_aspect_ratio:
        fp.write(b';preserveAspectRatio=0')
    fp.write(b':')
    fp.flush()

    buf_base64 = base64.b64encode(buf)
    fp.write(buf_base64)

    fp.write(ST)

    if is_tmux:
        # terminate DCS passthrough mode
        fp.write(TMUX_WRAP_ED)
        # move back the cursor lines down
        fp.write(CSI + b"%dE" % height)
        fp.write(CSI + b'?25h')
    else:
        fp.write(b'\n')

    # flush is needed so that the cursor control sequence can take effect
    fp.flush()


def main():
    import argparse
    try:
        from imgcat import __version__
    except ImportError:
        __version__ = 'N/A'

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', nargs='*', type=str,
                        help='Path to the images.')
    parser.add_argument('--height', default=None, type=int,
                        help='The number of rows (in terminal) for displaying images.')
    parser.add_argument('--width', default=None, type=int,
                        help='The number of columns (in terminal) for displaying images.')
    parser.add_argument('-v', '--version', action='version',
                        version='python-imgcat %s' % __version__)
    args = parser.parse_args()

    kwargs = dict()
    if args.height: kwargs['height'] = args.height
    if args.width: kwargs['width'] = args.width

    # read from stdin?
    if not sys.stdin.isatty():
        if not args.input or list(args.input) == ['-']:
            stdin = sys.stdin if IS_PY_2 else sys.stdin.buffer
            imgcat(to_content_buf(stdin), **kwargs)
            return 0
        else:
            sys.stderr.write("error: when reading from stdin, arg should not be given\n")
            return 1

    # imgcat from arguments
    for fname in args.input:
        # filename: open local file or download from web
        try:
            with io.open(fname, 'rb') as fp:
                buf = to_content_buf(fp)
        except IOError as e:
            sys.stderr.write(str(e))
            sys.stderr.write('\n')
            return (e.errno or 1)

        imgcat(buf, filename=os.path.basename(fname), **kwargs)

    if not args.input:
        parser.print_help()

    return 0


if __name__ == '__main__':
    sys.exit(main())
