`imgcat`
========

[![pypi](https://img.shields.io/pypi/v/imgcat.svg?maxAge=86400)](https://pypi.python.org/pypi/imgcat)
[![Build Status](https://travis-ci.org/wookayin/python-imgcat.svg?branch=master)](https://travis-ci.org/wookayin/python-imgcat)
[![license](https://img.shields.io/github/license/wookayin/python-imgcat.svg?maxAge=86400)](LICENSE)

The imgcat CLI, written in Python (and Python API, too).

<img src="https://raw.githubusercontent.com/wookayin/python-imgcat/master/screenshot.png" width="640" height="520" />

It works with [iTerm2](https://www.iterm2.com/documentation-images.html), and even inside tmux.


Installation and Usage
----------------------

```
pip install imgcat
```

Command-line interface (similar to [iTerm2's imgcat][iTerm2_imgcat]):

```bash
$ imgcat local_image.png
$ imgcat a.png b.png c.png
$ cat from_stdin.gif | imgcat

# height is 10 lines
$ imgcat a.png --height 10
```

Python API:

```python
>>> from imgcat import imgcat

# from the content of image (e.g. buffer in python3, str in python2)
>>> imgcat(open("./local_image.png"))

# or numpy arrays!
>>> im = skimage.data.chelsea()   # [300, 451, 3] ndarray, dtype=uint8
>>> imgcat(im, height=7)

# matplotlib, PIL.Image, etc.
>>> imgcat(Image.fromarray(im))

>>> import matplotlib.pyplot as plt
>>> fig, ax = plt.subplots(); ax.plot([1, 2, 3, 4, 5])
>>> imgcat(fig)
```

Matplotlib Backend: `module://imgcat`

```python
MPLBACKEND="module://imgcat" python draw_matplotlib.py
```

```python
>>> import matplotlib
>>> matplotlib.use("module://imgcat")

>>> import matplotlib.pyplot as plt
>>> fig, ax = plt.subplots()
>>> ax.text(0.5, 0.5, "Hello World!");
>>> fig.show()
# an image shall be displayed on your terminal!
```

Notes
-----

* Currently, [tmux 2.5+ cannot display big images][tmux_gh1502]. Use tmux <= 2.4 or run outside tmux.
* TODO: General platform/emulator support (introduce multiple backends)


Related Projects
----------------

* Original implementation: [imgcat][iTerm2_imgcat] from iTerm2  (limited tmux support)
  * There are modified versions with better tmux support by [Eric Dobson](https://gitlab.com/gnachman/iterm2/issues/3898#note_14097715) and by [@krtx](https://gist.github.com/krtx/533d33d6cc49ecbbb8fab0ae871059ec)
* Node.js: [term-img](https://github.com/sindresorhus/term-img) (no tmux support)
* Go: [iterm2-imagetools](https://github.com/olivere/iterm2-imagetools) (no tmux support)


[iTerm2_imgcat]: https://github.com/gnachman/iTerm2/blob/master/tests/imgcat
[tmux_gh1502]: https://github.com/tmux/tmux/issues/1502


License
-------

[MIT License](LICENSE)
