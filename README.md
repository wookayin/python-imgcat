`imgcat`
========

[![pypi](https://img.shields.io/pypi/v/imgcat.svg?maxAge=86400)](https://pypi.python.org/pypi/imgcat)
[![Build Status](https://travis-ci.org/wookayin/python-imgcat.svg?branch=master)](https://travis-ci.org/wookayin/python-imgcat)
[![license](https://img.shields.io/github/license/wookayin/python-imgcat.svg?maxAge=86400)](LICENSE)

The imgcat CLI, written in Python (and Python API, too).

<img src="https://raw.githubusercontent.com/wookayin/python-imgcat/master/screenshot.png" width="640" height="520" />

It works with [iTerm2](https://www.iterm2.com/documentation-images.html), and [even inside tmux][iterm_g3898].


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

IPython magic (works both in terminal and notebook)

```
%load_ext imgcat
%imgcat skimage.data.chelsea()
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
[iterm_g3898]: https://gitlab.com/gnachman/iterm2/issues/3898

Some benchmarks:
```
❯ hyperfine --warmup 5 "imgcat '/Users/evar/Base/_Art/ddg/her-heart/hd/OC I2.jpg' /Users/evar/Base/_Art/ddg/Me/dream_iegwzdmcfxy.jpg /Users/evar/Base/_Art/ddg/Me/dream_1j3y57rjc9a.jpg" "$GOBIN/imgcat '/Users/evar/Base/_Art/ddg/her-heart/hd/OC I2.jpg' /Users/evar/Base/_Art/ddg/Me/dream_iegwzdmcfxy.jpg /Users/evar/Base/_Art/ddg/Me/dream_1j3y57rjc9a.jp"

Benchmark #1: imgcat '/Users/evar/Base/_Art/ddg/her-heart/hd/OC I2.jpg' /Users/evar/Base/_Art/ddg/Me/dream_iegwzdmcfxy.jpg /Users/evar/Base/_Art/ddg/Me/dream_1j3y57rjc9a.jpg
  Time (mean ± σ):     575.1 ms ± 100.3 ms    [User: 451.4 ms, System: 121.2 ms]
  Range (min … max):   496.2 ms … 829.9 ms    10 runs

Benchmark #2: /Users/evar/go/bin/imgcat '/Users/evar/Base/_Art/ddg/her-heart/hd/OC I2.jpg' /Users/evar/Base/_Art/ddg/Me/dream_iegwzdmcfxy.jpg /Users/evar/Base/_Art/ddg/Me/dream_1j3y57rjc9a.jp
  Time (mean ± σ):      11.9 ms ±   4.6 ms    [User: 6.1 ms, System: 5.0 ms]
  Range (min … max):     7.5 ms …  31.7 ms    99 runs

  Warning: Statistical outliers were detected. Consider re-running this benchmark on a quiet PC without any interferences from other programs. It might help to use the '--warmup' or '--prepare' options.

Summary
  '/Users/evar/go/bin/imgcat '/Users/evar/Base/_Art/ddg/her-heart/hd/OC I2.jpg' /Users/evar/Base/_Art/ddg/Me/dream_iegwzdmcfxy.jpg /Users/evar/Base/_Art/ddg/Me/dream_1j3y57rjc9a.jp' ran
   48.42 ± 20.39 times faster than 'imgcat '/Users/evar/Base/_Art/ddg/her-heart/hd/OC I2.jpg' /Users/evar/Base/_Art/ddg/Me/dream_iegwzdmcfxy.jpg /Users/evar/Base/_Art/ddg/Me/dream_1j3y57rjc9a.jpg'
```
License
-------

[MIT License](LICENSE)
