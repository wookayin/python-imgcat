"""
Kitty backend for imgcat.
"""

import sys
import os
import base64
from collections import OrderedDict
from base64 import standard_b64encode


ESC = b'\033'

TMUX_WRAP_ST = b'\033Ptmux;'
TMUX_WRAP_ED = b'\033\\'


def serialize_gr_command(cmd, payload=None):
    cmd = ','.join('{}={}'.format(k, v) for k, v in cmd.items())
    ans = []
    w = ans.append

    is_tmux = 'TMUX' in os.environ and 'tmux' in os.environ['TMUX']

    if is_tmux:
        w(TMUX_WRAP_ST + b'\033') #!

    # kitty graphics sequence start
    w(b'\033_G'), w(cmd.encode('ascii'))

    if payload:
        w(b';')
        w(payload)

    if is_tmux:
        w(b'\033')  # escape \033

    # kitty graphics sequence end
    w(b'\033\\')

    if is_tmux:
        w(TMUX_WRAP_ED) #!

    return b''.join(ans)


def clear():
    """Send the sesquence for clearing all graphics."""
    is_tmux = 'TMUX' in os.environ and 'tmux' in os.environ['TMUX']
    seq = []
    w = seq.append

    if is_tmux:
        w(b'\033Ptmux;\033')

    w(b'\033_Ga=d,d=A')
    if is_tmux:
        w(b'\033')
    w(b'\033\\')

    if is_tmux:
        w(b'\033\\')

    sys.stdout.buffer.write(b''.join(seq))


def _write_image(buf, fp, height):
    # https://sw.kovidgoyal.net/kitty/graphics-protocol.html
    # print some blank lines
    is_tmux = 'TMUX' in os.environ and 'tmux' in os.environ['TMUX']
    if is_tmux:
        CSI = b'\033['
        fp.write(b'\n' * height)
        fp.write(CSI + b'?25l')
        fp.write(CSI + str(height).encode() + b"F")     # PEP-461
        fp.flush()

    cmd = OrderedDict([
        ('a', 'T'),
        ('f', 100),
    ])
    write_chunked(cmd, buf)

    # move back the cursor
    if is_tmux:
        fp.write(CSI + str(height).encode() + b"E")
        fp.write(CSI + b'?25h')
        fp.flush()


def write_chunked(cmd, data):
    data = standard_b64encode(data)
    while data:
        chunk, data = data[:4096], data[4096:]
        m = 1 if data else 0
        cmd['m'] = m
        sys.stdout.buffer.write(serialize_gr_command(cmd, chunk))
        sys.stdout.flush()
        cmd.clear()


if __name__ == '__main__':
    with open(sys.argv[-1], 'rb') as f:
        _write_image(fp=sys.stdout.buffer, buf=f.read(), height=10)


__all__ = (
    'clear',
    '_write_image',
)
