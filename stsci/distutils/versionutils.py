"""Utilities for dealing with package version info.

See also stsci.distutils.svnutils which specifically deals with adding SVN
info to version.py modules.
"""


from __future__ import with_statement

import datetime
import os
import subprocess

from stsci.distutils.astutils import ImportVisitor, walk


VERSION_PY_TEMPLATE = """
\"\"\"This is an automatically generated file created by %(hook_function)s.  Do
not modify this file by hand.
\"\"\"


import datetime

try:
    import pkg_resources
except ImportError:
    pkg_resources = None


__version__ = %(version)r
__svn_revision__ = %(svn_revision)r
__svn_full_info__ = %(svn_full_info)r
__setup_datetime__ = %(setup_datetime)r


# Update the SVN info if installed in develop mode
if pkg_resources:
    dist = pkg_resources.get_distribution(%(name)r)
    if dist.precedence == pkg_resources.DEVELOP_DIST:
        import os
        import subprocess

        # Wind up the module path until we find the root of the project
        # containing setup.py
        path = os.path.abspath(os.path.dirname(__file__))
        while path and not os.path.exists(os.path.join(path, 'setup.py')):
            path = os.path.dirname(path)
        if path:
            try:
                pipe = subprocess.Popen(['svnversion', path],
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)
                if pipe.wait() == 0:
                    stdout = pipe.stdout.read().decode('ascii').strip()
                    __svn_revision__ = stdout
            except OSError:
                __svn_revision__ = ''

            try:
                pipe = subprocess.Popen(['svn', 'info', path],
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)
                if pipe.wait() == 0:
                    lines = []
                    for line in pipe.stdout.readlines():
                        line = line.decode('ascii').strip()
                        if not line:
                            continue
                        lines.append(line)

                    if not lines:
                        __svn_full_info__ = 'unknown'
                    else:
                        __svn_full_info__ = '\\n'.join(lines)
            except OSError:
                __svn_full_info__ = 'unknown'
"""


def package_uses_version_py(package_root, package, module_name='version'):
    """Determines whether or not a version.py module should exist in the given
    package.  Returns the full path to the version.py module, regardless of
    whether it already exists.  Otherwise returns False.

    This works by checking whether or not there are any imports from 'version'
    in the package's __init__.py.
    """

    pdir = os.path.join(package_root, *(package.split('.')))
    init = os.path.join(pdir, '__init__.py')
    if not os.path.exists(init):
        # Not a valid package
        # TODO: Maybe issue a warning here?
        return False

    try:
        visitor = ImportVisitor()
        walk(init, visitor)
    except SyntaxError:
        # TODO: Maybe issue a warning?
        pass

    found = False
    # Check the import statements parsed from the file for an import of or
    # from the svninfo module in this package
    for imp in visitor.imports:
        if imp[0] in (module_name, '.'.join((package, module_name))):
            found = True
            break
    for imp in visitor.importfroms:
        mod = imp[0]
        name = imp[1]
        if (mod in (module_name, '.'.join((package, module_name))) or
            (mod == package and name == module_name)):
            found = True
            break

    if not found:
        return False

    return os.path.join(pdir, module_name + '.py')


def clean_version_py(package_dir, package):
    """Removes the generated version.py module from a package, but only if
    we're in an SVN working copy.
    """

    pdir = os.path.join(package_root, *(package.split('.')))
    version_py = os.path.join(pdir, 'version.py')
    if not os.path.exists(svninfo):
        return

    try:
        pipe = subprocess.Popen(['svn', 'status', svninfo],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
    except OSError:
        return

    if pipe.wait() != 0:
        return

    # TODO: Maybe don't assume ASCII here.  Find out the best way to handle
    # this.
    if not pipe.stdout.read().decode('ascii').startswith('?'):
        return

    os.remove(version_py)


def update_setup_datetime(filename='version.py'):
    """Update the version.py with the last time a setup command was run."""

    if not os.path.exists(filename):
        return

    d = datetime.datetime.now()

    lines = []
    with open(filename, 'r') as f:
        lines = f.readlines()

    with open(filename, 'w') as f:
        for line in lines:
            if not line.startswith('__setup_datetime__'):
                f.write(line)
            else:
                f.write('__setup_datetime__ = %r\n' % d)
