"""
The imgcat module
"""

__version__ = '0.6.0.dev0'


from .imgcat import (
    imgcat,
    clear,
    main
)

try:
    # support module://imgcat backend
    from .mpl_backend import (
        new_figure_manager, show
    )
except ImportError:
    # matplotlib is not available, do nothing
    pass


# IPython magic support: %load_ext imgcat
def load_ipython_extension(ipython):
    from .ipython_magic import ImgcatMagics
    ipython.register_magics(ImgcatMagics)
