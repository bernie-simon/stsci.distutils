from __future__ import with_statement

import contextlib

try:
    reload = reload
except NameError:
    from imp import reload

from ConfigParser import ConfigParser
from distutils.ccompiler import new_compiler, customize_compiler


@contextlib.contextmanager
def open_config(filename):
    cfg = ConfigParser()
    cfg.read(filename)
    yield cfg
    with open(filename, 'w') as fp:
        cfg.write(fp)


def get_compiler_command():
    """
    Returns the name of the executable used by the default compiler on the
    system used by distutils to build C extensions.
    """

    compiler = new_compiler()
    customize_compiler(compiler)
    return compiler.compiler[0]
