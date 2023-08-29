import codecs
import contextlib
import functools
import hashlib
import io
import os
import sys

import matplotlib
import numpy as np
import pytest

if (not os.environ.get('DISPLAY', '') or \
    not matplotlib.rcParams.get('backend', None)
    ):
    matplotlib.use('Agg')

from imgcat import imgcat


@pytest.fixture
def mock_env(monkeypatch, env_profile):
    """Mock environment variables (especially, TMUX)"""
    if env_profile == 'plain':
        monkeypatch.delenv("TMUX", raising=False)
    elif env_profile == 'tmux':
        monkeypatch.setenv("TMUX", "mock-tmux-session")
    else:
        raise ValueError("Unknown profile: " + str(env_profile))


def parametrize_env(callable, env_profiles=['plain', 'tmux']):

    @pytest.mark.usefixtures('mock_env')
    @pytest.mark.parametrize('env_profile', env_profiles)
    @functools.wraps(callable)
    def _wrapped(*args, **kwargs):
        return callable(*args, **kwargs)

    return _wrapped


class TestImgcat:
    '''Basic unit test. Supports TMUX and non-TMUX environment mocking.'''

    def setUp(self):
        sys.stdout.write('\n')

    def tearDown(self):
        # Under verbose mode in unit test, make sure that flush stdout
        # so that the image can be displayed immediately at proper positions
        sys.stdout.flush()

    @contextlib.contextmanager
    def _redirect_stdout(self, reprint=True):
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
            stdout_buf = sys.stdout.buffer
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
        with self._redirect_stdout(reprint=True) as f:
            yield

        captured_bytes = f.getvalue()

        is_tmux = os.getenv('TMUX')
        if is_tmux:
            captured_bytes = self.tmux_unwrap_passthrough(captured_bytes)
        self._validate_iterm2(captured_bytes, **kwargs)

    @staticmethod
    def tmux_unwrap_passthrough(b: bytes) -> bytes:
        '''Strip out all tmux pass-through sequence and other cursor-movement
        control sequences that come either in the beginning or in the end.'''
        assert isinstance(b, bytes)
        #assert b.startswith(b'\033Ptmux;')
        #assert b.endswith(b'\033\\')
        try:
            st = b.index(b'\033Ptmux;')
            ed = b.rindex(b'\033\\')
        except ValueError:
            assert False, "Does not contain \\033Ptmux; ..."

        b = b[st + 7 : ed]
        b = b.replace(b'\033\033', b'\033')
        return b

    # ----------------------------------------------------------------------
    # Basic functionality tests

    @parametrize_env
    def test_numpy(self):
        # TODO: The test fails if tmux is enabled

        # uint8, grayscale
        a = np.ones([32, 32], dtype=np.uint8) * 128
        with self.capture_and_validate():
            imgcat(a)

        # uint8, color image
        with self.capture_and_validate():
            a = np.ones([32, 32, 3], dtype=np.uint8) * 0
            a[:, :, 0] = 255  # (255, 0, 0): red
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

    @parametrize_env
    def test_tensorflow(self):
        try:
            import tensorflow.compat.v2 as tf  # type: ignore # noqa
        except ImportError:
            pytest.skip("No tensorflow available")

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

    @parametrize_env
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
    sys.exit(pytest.main(["-s", "-v"] + sys.argv))
