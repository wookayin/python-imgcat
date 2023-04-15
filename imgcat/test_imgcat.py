# -*- coding: utf-8 -*-

import unittest
import numpy as np
import sys
import os
import io
import re
import hashlib
import functools
import contextlib

import pytest

import matplotlib
if not os.environ.get('DISPLAY', '') or not matplotlib.rcParams.get('backend', None):
    matplotlib.use('Agg')

from imgcat import imgcat


IS_PY_2 = (sys.version_info[0] <= 2)
IS_PY_3 = (not IS_PY_2)


@pytest.fixture
def mock_env(monkeypatch, term_profile, tmux_profile):
    """Mock environment variables (especially, TMUX)"""
    if tmux_profile == 'plain':
        monkeypatch.delenv("TMUX", raising=False)
    elif tmux_profile == 'tmux':
        monkeypatch.setenv("TMUX", "mock-tmux-session")
    else:
        raise ValueError("Unknown tmux_profile: " + str(tmux_profile))

    if term_profile == 'iterm2':
        pass  # default
    elif term_profile == 'kitty':
        monkeypatch.setenv("TERM", 'xterm-kitty')
    else:
        raise ValueError("Unknown term_profile: " + str(term_profile))


def parametrize_env(callable,
                    tmux_profiles=['plain', 'tmux'],
                    term_profiles=['iterm2', 'kitty'],
                    ):
    @pytest.mark.usefixtures('mock_env')
    @pytest.mark.parametrize('term_profile', term_profiles)
    @pytest.mark.parametrize('tmux_profile', tmux_profiles)
    @functools.wraps(callable)
    def _wrapped(*args, **kwargs):
        return callable(*args, **kwargs)
    return _wrapped


class TestImgcat(object):
    '''Basic unit test. Supports TMUX and non-TMUX environment mocking.'''

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

    def _validate_kitty(self, buf):
        """Check if graphics sequence is correct."""
        assert isinstance(buf, bytes)

        # https://sw.kovidgoyal.net/kitty/graphics-protocol/#remote-client
        # f=100 indicates PNG data
        # m=0 means the last chunk, m=1 means other chunk will follow
        assert re.match(b'^\x1b_Ga=T,f=100,m=(0|1);', buf)
        assert buf.endswith(b'\033\\')

        # TODO: test control sequences that come in multiple chunks.
        # in such cases, only the last chunk have m=0 and the rest have m=1.


    @contextlib.contextmanager
    def capture_and_validate(self, **kwargs):
        with self._redirect_stdout(reprint=True) as f:
            yield

        captured_bytes = f.getvalue()

        is_tmux = os.getenv('TMUX')
        if is_tmux:
            captured_bytes = self.tmux_unwrap_passthrough(captured_bytes)

        if 'kitty' in os.getenv('TERM', ''):
            self._validate_kitty(captured_bytes, **kwargs)
        else:
            self._validate_iterm2(captured_bytes, **kwargs)

    @staticmethod
    def tmux_unwrap_passthrough(b):
        '''Strip out all tmux pass-through sequence and other cursor-movement
        control sequences that come either in the beginning or in the end.'''
        assert isinstance(b, bytes)
        try:
            st = b.index(b'\033Ptmux;')
            ed = b.rindex(b'\033\\')
        except ValueError:
            assert '\033Ptmux;' in b, "Does not contain \\033Ptmux; ..."

        b = b[st + 7 : ed]
        b = b.replace(b'\033\033', b'\033')
        return b

    # ----------------------------------------------------------------------
    # Basic functionality tests

    @parametrize_env
    def test_numpy(self):
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
    @unittest.skipIf(sys.platform == 'darwin', "Lacking arm64 mac support")
    @parametrize_env
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
    @unittest.skipIf(sys.platform == 'darwin', "Lacking arm64 mac support")
    @parametrize_env
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

    @parametrize_env
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

    @parametrize_env
    def test_pil(self):
        from PIL import Image
        a = np.ones([32, 32], dtype=np.uint8) * 255
        im = Image.fromarray(a)
        imgcat(im)

    @parametrize_env
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

    @parametrize_env
    def test_invalid_data(self):
        # invalid bytes. TODO: capture stderr
        with self.capture_and_validate():
            invalid = b'0' * 32
            imgcat(invalid)

    # ----------------------------------------------------------------------
    # Arguments, etc.

    @parametrize_env
    def test_args_filename(self):
        gray = np.ones([32, 32], dtype=np.uint8) * 128
        imgcat(gray, filename='foo.png')
        imgcat(gray, filename='unicode_한글.png')

    # Only available in iTerm2 (not kitty)
    @functools.partial(parametrize_env, term_profiles=['iterm2'])
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
