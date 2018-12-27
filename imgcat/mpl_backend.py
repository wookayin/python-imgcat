# based on https://github.com/matplotlib/matplotlib/blob/master/lib/matplotlib/backends/backend_template.py

import types

from matplotlib._pylab_helpers import Gcf
from matplotlib.figure import Figure
from matplotlib.backend_bases import (
     FigureCanvasBase, FigureManagerBase, GraphicsContextBase, RendererBase)

from . import imgcat
assert isinstance(imgcat, types.FunctionType)


class FigureManagerImgcat(FigureManagerBase):
    def show(self):
        canvas = self.canvas
        imgcat(canvas.figure)


def show(block=None):
    for manager in Gcf.get_all_fig_managers():
        manager.show()

        # Do not re-display what is already shown.
        Gcf.destroy(manager.num)


def new_figure_manager(num, *args, **kwargs):
    FigureClass = kwargs.pop('FigureClass', Figure)
    fig = FigureClass(*args, **kwargs)
    return new_figure_manager_given_figure(num, fig)


def new_figure_manager_given_figure(num, figure):
    # this must be lazy-loaded to avoid unwanted configuration of mpl backend
    from matplotlib.backends.backend_agg import FigureCanvasAgg

    canvas = FigureCanvasAgg(figure)
    manager = FigureManagerImgcat(canvas, num)
    return manager


#FigureManager = FigureManagerImgcat
#FigureCanvas = FigureCanvasAgg
