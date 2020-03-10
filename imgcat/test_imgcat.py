# -*- coding: utf-8 -*-

import unittest
import numpy as np
import sys
import os
import io

from imgcat import imgcat

import matplotlib
if not os.environ.get('DISPLAY', '') or not matplotlib.rcParams.get('backend', None):
    matplotlib.use('Agg')


class TestExample(unittest.TestCase):
    '''
    Basic unit test.

    TODO: tmux handling, CLI interface, etc.
    '''

    def setUp(self):
        sys.stdout.write('\n')

    def tearDown(self):
        # Under verbose mode in unit test, make sure that flush stdout
        # so that the image can be displayed immediately at proper positions
        sys.stdout.flush()

    # ----------------------------------------------------------------------
    # Basic functionality tests

    def test_numpy(self):
        # uint8, grayscale
        a = np.ones([32, 32], dtype=np.uint8) * 128
        imgcat(a)

        # uint8, color image
        a = np.ones([32, 32, 3], dtype=np.uint8) * 0
        a[:, :, 0] = 255    # (255, 0, 0): red
        imgcat(a)

        # np.float32 [0..1] (#7f7f7f)
        a = np.ones([32, 32, 3], dtype=np.float32) * 0.5
        imgcat(a)

        # np.float64 [0..1] (#37b24d)
        a = np.ones([32, 32, 3], dtype=np.float64) * 0.5
        a[..., 0], a[..., 1], a[..., 2] = 0x37 / 255., 0xb2 / 255., 0x4d / 255.
        imgcat(a)

    @unittest.skipIf(sys.version_info < (3, 5), "Only in Python 3.5+")
    def test_torch(self):
        import torch

        # uint8, grayscale
        a = torch.ones([1, 32, 32], dtype=torch.uint8)
        imgcat(a)

        a = torch.ones([1, 32, 32], dtype=torch.float32)
        imgcat(a)

        # uint8, color image
        a = torch.ones([3, 32, 32], dtype=torch.uint8) * 0
        imgcat(a)

    @unittest.skipIf(sys.version_info < (3, 5), "Only in Python 3.5+")
    def test_tensorflow(self):
        import tensorflow.compat.v2 as tf
        tf.enable_v2_behavior()
        assert tf.executing_eagerly(), "Eager execution should be enabled."

        # #37b24d
        a = tf.constant([0x37, 0xb2, 0x4d], dtype=tf.uint8)
        a = tf.tile(a[None, None, :], [32, 32, 1])  # [32, 32, 3]
        imgcat(a)

        # float32 tensors
        a = tf.fill([32, 32, 3], 0.5)
        a = tf.cast(a, dtype=tf.float32)
        imgcat(a)

    def test_matplotlib(self):
        # plt
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(2, 2))
        ax.plot([0, 1])
        fig.tight_layout()
        imgcat(fig)

        # without canvas
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
        png = base64.b64decode(b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAACklEQVR4nGMAAQAABQABDQottAAAAABJRU5ErkJggg==')
        imgcat(png)

        # JPG
        # https://github.com/mathiasbynens/small/blob/master/jpeg.jpg
        jpg = base64.b64decode(b'/9j/2wBDAAMCAgICAgMCAgIDAwMDBAYEBAQEBAgGBgUGCQgKCgkICQkKDA8MCgsOCwkJDRENDg8QEBEQCgwSExIQEw8QEBD/yQALCAABAAEBAREA/8wABgAQEAX/2gAIAQEAAD8A0s8g/9k=')
        imgcat(jpg)

        # GIF
        # http://probablyprogramming.com/2009/03/15/the-tiniest-gif-ever
        gif = base64.b64decode(b'R0lGODlhAQABAIABAP///wAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==')
        imgcat(gif)

        # invalid bytes. TODO: capture stderr
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
