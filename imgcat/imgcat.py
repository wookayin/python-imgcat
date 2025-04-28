"""
imgcat in Python.
"""

from typing import Any, Optional, TYPE_CHECKING, Tuple

import contextlib
import io
import os
import struct
import subprocess
import sys
from urllib.request import urlopen

HELP_EPILOG = """
SIZES

Sizes can be specified as (N is any integer):
    * N:        Number of character cells.
    * Npx:      Pixels.
    * N%:       Percentage of session's size.
    * auto:     Use the original dimension, but allow scaling above this (terminal dependent?).
    * original: Use the original dimension.
    * default:  Let the terminal decide.
    * v0.5:     Height only; use smaller of terminal height or original pixels/24 rows.

Where aspect is preserved, the smaller dimension will be used.
The scaling is performed by your terminal, except in v0.5 mode. On Konsole, the image will be scaled to the largest size which fits the constraints, except that 'auto' is ignored.
The defaults are --width=100% --height=original
"""

if TYPE_CHECKING:
    import matplotlib.figure  # type: ignore
    import torch  # type: ignore
    from PIL import Image  # type: ignore


def get_image_shape(buf: bytes) -> Tuple[Optional[int], Optional[int]]:
    '''
    Extracts image shape as 2-tuple (width, height) from the content buffer.

    Supports GIF, PNG and other image types (e.g. JPEG) if PIL/Pillow is installed.
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
        # everything else: get width/height from PIL
        # TODO: it might be inefficient to write again the memory-loaded content to buffer...
        b = io.BytesIO()
        b.write(buf)

        try:
            import PIL   # noqa
        except ImportError:
            # PIL not available
            sys.stderr.write("Warning: cannot determine the image size; please install Pillow" + "\n")
            sys.stderr.flush()
            return None, None

        from PIL import Image, UnidentifiedImageError
        try:
            im = Image.open(b)
            return im.width, im.height
        except UnidentifiedImageError:
            # PIL.Image.open throws an error -- probably invalid byte input are given
            sys.stderr.write("Warning: PIL cannot identify image size; this may not be an image file" + "\n")
            return None, None
        finally:
            b.close()


def _isinstance(obj, module, clsname):
    """A helper that works like isinstance(obj, module:clsname), but even when
    the module hasn't been imported or the type is not importable."""

    if module not in sys.modules:
        return False

    try:
        clstype = getattr(sys.modules[module], clsname)
        return isinstance(obj, clstype)
    except AttributeError:
        return False


def to_content_buf(data: Any) -> bytes:
    # TODO: handle 'stream-like' data efficiently, rather than storing into RAM

    if isinstance(data, bytes):
        return data

    elif isinstance(data, io.BufferedReader):
        buf = data
        return buf.read()

    elif isinstance(data, io.TextIOWrapper):
        return data.buffer.read()

    elif _isinstance(data, 'numpy', 'ndarray'):
        # numpy ndarray: convert to png
        import numpy
        im: 'numpy.ndarray' = data
        if len(im.shape) == 2:
            mode = 'L'     # 8-bit pixels, grayscale
            im = im.astype(sys.modules['numpy'].uint8)
        elif len(im.shape) == 3 and im.shape[2] in (1, 3, 4):
            # (H, W, C) format
            mode = None    # RGB/RGBA
            if im.dtype.kind == 'f':
                im = (im * 255).astype('uint8')
            if im.shape[2] == 1:
                mode = 'L'  # 8-bit grayscale
                im = numpy.squeeze(im, axis=2)
        elif len(im.shape) == 3 and im.shape[0] in (1, 3, 4):
            # (C, H, W) format
            mode = None    # RGB/RGBA
            im = numpy.rollaxis(im, 0, 3)  # CHW -> HWC
            if im.dtype.kind == 'f':
                im = (im * 255).astype('uint8')
            if im.shape[2] == 1:
                mode = 'L'  # 8-bit grayscale
                im = numpy.squeeze(im, axis=2)
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
            # mode: https://pillow.readthedocs.io/en/4.2.x/handbook/concepts.html#concept-modes
            Image.fromarray(im, mode=mode).save(buf, format='png')
            return buf.getvalue()

    elif hasattr(data, '__array__'):
        # e.g., JAX tensors
        arr_img = data.__array__()
        return to_content_buf(arr_img)

    elif _isinstance(data, 'torch', 'Tensor'):
        torch_img: 'torch.Tensor' = data
        return to_content_buf(torch_img.numpy())

    elif _isinstance(data, 'tensorflow.python.framework.ops', 'EagerTensor'):
        tf_img: Any = data
        return to_content_buf(tf_img.numpy())

    elif _isinstance(data, 'PIL.Image', 'Image'):
        # PIL/Pillow images
        img: 'Image.Image' = data

        with io.BytesIO() as buf:
            img.save(buf, format='png')
            return buf.getvalue()

    elif _isinstance(data, 'matplotlib.figure', 'Figure'):
        # matplotlib figures
        fig: 'matplotlib.figure.Figure' = data
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


def imgcat(data: Any, filename=None,
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
        fp = sys.stdout.buffer

    buf = to_content_buf(data)
    if len(buf) == 0:
        raise ValueError("Empty buffer")

    if height == 'v0.5' or 'original' in (height, width):
        im_width, im_height = get_image_shape(buf)
        if height == 'v0.5':
            if im_height:
                assert pixels_per_line > 0
                height = (im_height + (pixels_per_line - 1)) // pixels_per_line

                # automatically limit height to the current tty,
                # otherwise the image will be just erased
                try:
                    tty_height, _ = get_tty_size()
                    height = max(1, min(height, tty_height - 9))
                except OSError:
                    # may not be a terminal
                    pass
            else:
                # image height unavailable, fallback?
                height = 10
        elif height == 'original':
            height = f'{im_height}px' if im_height else 'auto'
        if width == 'original':
            width = f'{im_width}px' if im_width else 'auto'

    if width == 'v0.5':
        raise ValueError("There is no legacy fallback for width")

    from . import iterm2
    iterm2._write_image(buf, fp,
                        filename=filename, width=width, height=height,
                        preserve_aspect_ratio=preserve_aspect_ratio)


def parse_size(s):
    if s in ("v0.5", "auto", "original"):
        return s
    if s == 'default':
        return None
    for suffix in ("%", "px", ""):
        if s.endswith(suffix):
            return f"{int(s[:-len(suffix)])}{suffix}"

def main():
    import argparse
    try:
        from imgcat import __version__
    except ImportError:
        __version__ = 'N/A'

    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog=HELP_EPILOG,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument('input', nargs='*', type=str,
                        help='Path to the images.')
    parser.add_argument('--height', default='original', type=parse_size,
                        help='Height of image.')
    parser.add_argument('--width', default='100%', type=parse_size,
                        help='Width of image.')
    parser.add_argument('--no-preserve-aspect', action='store_true',
                        help='Allow reshaping of image.')
    parser.add_argument('-v', '--version', action='version',
                        version='python-imgcat %s' % __version__)
    args = parser.parse_args()

    kwargs = dict()
    if args.height:
        kwargs['height'] = args.height
    if args.width:
        kwargs['width'] = args.width
    kwargs['preserve_aspect_ratio'] = not args.no_preserve_aspect

    # read from stdin?
    if not sys.stdin.isatty():
        if not args.input or list(args.input) == ['-']:
            stdin = sys.stdin.buffer
            imgcat(to_content_buf(stdin), **kwargs)
            return 0

    # imgcat from arguments
    for fname in args.input:
        # filename: open local file or download from web
        try:
            if fname.startswith('http://') or fname.startswith('https://'):
                with contextlib.closing(urlopen(fname)) as fp:
                    buf = fp.read()  # pylint: disable=no-member
            else:
                with io.open(fname, 'rb') as fp:
                    buf = fp.read()
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
