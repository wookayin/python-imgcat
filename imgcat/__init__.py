"""
The imgcat module
"""

__version__ = '0.6.0'


from .imgcat import imgcat as imgcat
from .imgcat import main as main

try:
    # support module://imgcat backend
    from .mpl_backend import new_figure_manager as new_figure_manager
    from .mpl_backend import show as show
    from .mpl_backend import FigureCanvas as FigureCanvas
except ImportError:
    # matplotlib is not available, do nothing
    pass


# IPython magic support: %load_ext imgcat
def load_ipython_extension(ipython):
    from .ipython_magic import ImgcatMagics
    ipython.register_magics(ImgcatMagics)
