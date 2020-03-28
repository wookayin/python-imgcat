# -*- coding: utf-8 -*-

import unittest
import numpy as np
import sys
import os
import io
import hashlib

from imgcat import imgcat

import matplotlib
import contextlib
if not os.environ.get('DISPLAY', '') or not matplotlib.rcParams.get('backend', None):
    matplotlib.use('Agg')


IS_PY_2 = (sys.version_info[0] <= 2)
IS_PY_3 = (not IS_PY_2)


class TestImgcat(unittest.TestCase):
    '''Basic unit test.
    TODO: tmux handling, CLI interface, etc.'''

    def setUp(self):
        sys.stdout.write('\n')

    def tearDown(self):
        # Under verbose mode in unit test, make sure that flush stdout
        # so that the image can be displayed immediately at proper positions
        sys.stdout.flush()

    @contextlib.contextmanager
    def _redirect_stdout(self, reprint=True):
        # TODO: python 2?
        import io, codecs
        buf = io.BytesIO()
        out = codecs.getwriter('utf-8')(buf)
        setattr(out, 'buffer', buf)

        try:
            _original_stdout = getattr(sys, 'stdout')
            setattr(sys, 'stdout', out)
            yield out
        finally:
            setattr(sys, 'stdout', _original_stdout)
            del _original_stdout

        if reprint:
            stdout_buf = sys.stdout.buffer if IS_PY_3 else sys.stdout
            stdout_buf.write(buf.getvalue())
            stdout_buf.flush()

    def _validate_iterm2(self, buf, sha1=None):
        assert isinstance(buf, bytes)

        # check if graphics sequence is correct
        assert buf.startswith(b'\x1b]1337;')
        assert buf.endswith(b'\x07\n') or buf.endswith(b'\x07')

        if sha1:
            assert hashlib.sha1(buf).hexdigest().startswith(sha1), ("SHA1 mismatch")

    @contextlib.contextmanager
    def capture_and_validate(self, **kwargs):
        with self._redirect_stdout() as f:
            yield
        self._validate_iterm2(f.getvalue(), **kwargs)

    # ----------------------------------------------------------------------
    # Basic functionality tests

    def test_numpy(self):
        # TODO: The test fails if tmux is enabled

        # uint8, grayscale
        a = np.ones([32, 32], dtype=np.uint8) * 128
        with self.capture_and_validate():
            imgcat(a)

        # uint8, color image
        with self.capture_and_validate():
            a = np.ones([32, 32, 3], dtype=np.uint8) * 0
            a[:, :, 0] = 255    # (255, 0, 0): red
            imgcat(a)

        # np.float32 [0..1] (#7f7f7f)
        with self.capture_and_validate():
            a = np.ones([32, 32, 3], dtype=np.float32) * 0.5
            imgcat(a)

        # np.float64 [0..1] (#37b24d)
        with self.capture_and_validate():
            a = np.ones([32, 32, 3], dtype=np.float64) * 0.5
            a[..., 0], a[..., 1], a[..., 2] = 0x37 / 255., 0xb2 / 255., 0x4d / 255.
            imgcat(a)

    @unittest.skipIf(sys.version_info < (3, 5), "Only in Python 3.5+")
    def test_torch(self):
        import torch

        # uint8, grayscale
        with self.capture_and_validate():
            a = torch.ones([1, 32, 32], dtype=torch.uint8)
            imgcat(a)

        with self.capture_and_validate():
            a = torch.ones([1, 32, 32], dtype=torch.float32)
            imgcat(a)

        # uint8, color image
        with self.capture_and_validate():
            a = torch.ones([3, 32, 32], dtype=torch.uint8) * 0
            imgcat(a)

    @unittest.skipIf(sys.version_info < (3, 5), "Only in Python 3.5+")
    def test_tensorflow(self):
        import tensorflow.compat.v2 as tf
        tf.enable_v2_behavior()
        assert tf.executing_eagerly(), "Eager execution should be enabled."

        # #37b24d
        with self.capture_and_validate():
            a = tf.constant([0x37, 0xb2, 0x4d], dtype=tf.uint8)
            a = tf.tile(a[None, None, :], [32, 32, 1])  # [32, 32, 3]
            imgcat(a)

        # float32 tensors
        with self.capture_and_validate():
            a = tf.fill([32, 32, 3], 0.5)
            a = tf.cast(a, dtype=tf.float32)
            imgcat(a)

    def test_matplotlib(self):
        # plt
        with self.capture_and_validate():
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=(2, 2))
            ax.plot([0, 1])
            fig.tight_layout()
            imgcat(fig)

        # without canvas
        with self.capture_and_validate():
            import matplotlib.figure
            fig = matplotlib.figure.Figure(figsize=(2, 2))
            imgcat(fig)

    def test_pil(self):
        from PIL import Image
        a = np.ones([32, 32], dtype=np.uint8) * 255
        im = Image.fromarray(a)
        imgcat(im)

    def test_bytes(self):
        '''Test imgcat from byte-represented image.
        TODO: validate height, filesize from the imgcat output sequences.'''
        import base64

        # PNG
        # https://github.com/mathiasbynens/small/blob/master/png-transparent.png
        with self.capture_and_validate():
            png = base64.b64decode(b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAACklEQVR4nGMAAQAABQABDQottAAAAABJRU5ErkJggg==')
            imgcat(png)

        # JPG
        # https://github.com/mathiasbynens/small/blob/master/jpeg.jpg
        with self.capture_and_validate():
            jpg = base64.b64decode(b'/9j/2wBDAAMCAgICAgMCAgIDAwMDBAYEBAQEBAgGBgUGCQgKCgkICQkKDA8MCgsOCwkJDRENDg8QEBEQCgwSExIQEw8QEBD/yQALCAABAAEBAREA/8wABgAQEAX/2gAIAQEAAD8A0s8g/9k=')
            imgcat(jpg)

        # GIF
        # http://probablyprogramming.com/2009/03/15/the-tiniest-gif-ever
        with self.capture_and_validate():
            gif = base64.b64decode(b'R0lGODlhAQABAIABAP///wAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==')
            imgcat(gif)

    def test_invalid_data(self):
        # invalid bytes. TODO: capture stderr
        with self.capture_and_validate():
            invalid = b'0' * 32
            imgcat(invalid)

    # ----------------------------------------------------------------------
    # Arguments, etc.

    def test_args_filename(self):
        gray = np.ones([32, 32], dtype=np.uint8) * 128
        imgcat(gray, filename='foo.png')
        imgcat(gray, filename='unicode_한글.png')

    def test_args_another(self):
        b = io.BytesIO()

        gray = np.ones([32, 32], dtype=np.uint8) * 128
        imgcat(gray, filename='foo.png', width=10, height=12,
               preserve_aspect_ratio=False, fp=b)

        v = b.getvalue()
        assert b'size=82;' in v
        assert b'height=12;' in v
        assert b'width=10;' in v
        assert b'name=Zm9vLnBuZw==;' in v   # foo.png
        assert b'preserveAspectRatio=0' in v


if __name__ == '__main__':
    unittest.main()
