"""
The imgcat module
"""

__version__ = '0.3.0'


from .imgcat import (
    imgcat,
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
