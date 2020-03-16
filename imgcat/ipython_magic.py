from IPython.core.magic import (Magics, magics_class, line_magic)
from IPython.display import display as ipython_display
from IPython.display import Markdown

import io
import os
import PIL.Image


def _is_ipython_notebook():
    try:
        # pylint: disable=undefined-variable
        return 'IPKernelApp' in get_ipython().config
        # pylint: enable=undefined-variable
    except:
        return False

IS_NOTEBOOK = _is_ipython_notebook()


@magics_class
class ImgcatMagics(Magics):
    # TODO: Add tests for ipython magic.

    @line_magic
    def imgcat(self, line=''):
        '''%imgcat magic, equivalent to imgcat(<expression>).

        Usage: %imgcat <expression>
        '''
        if not line:
            ipython_display(Markdown("Usage: `%imgcat [python code]`"))
            return

        if os.path.isfile(line):
            with open(line, mode='rb') as fp:
                ret = fp.read()
        else:
            global_ns = self.shell.user_global_ns
            local_ns = self.shell.user_ns

            ret = eval(line, global_ns, local_ns)  # pylint: disable=eval-used

        if IS_NOTEBOOK:
            from .imgcat import to_content_buf
            buf = io.BytesIO(to_content_buf(ret))
            im = PIL.Image.open(buf)
            ipython_display(im)
            buf.close()
        else:
            from .imgcat import imgcat
            imgcat(ret)
