from __future__ import with_statement

import datetime
import glob
import os
import string
import sys

from distutils import log


try:
    from packaging.util import split_multiline
except ImportError:
    try:
        from distutils2.util import split_multiline
    except ImportError:
        from d2to1.util import split_multiline


try:
    reload
except NameError:
    from imp import reload


from .svnutils import get_svn_info, get_svn_version
from .versionutils import (package_uses_version_py, clean_version_py,
                           update_setup_datetime, VERSION_PY_TEMPLATE)


def is_display_option(ignore=None):
    """A hack to test if one of the arguments passed to setup.py is a display
    argument that should just display a value and exit.  If so, don't bother
    running this hook (this capability really ought to be included with
    distutils2).

    Optionally, ignore may contain a list of display options to ignore in this
    check.  Each option in the ignore list must contain the correct number of
    dashes.
    """

    from setuptools.dist import Distribution

    # If there were no arguments in argv (aside from the script name) then this
    # is an implied display opt
    if len(sys.argv) < 2:
        return True

    display_opts = ['--command-packages', '--help', '-h']

    for opt in Distribution.display_options:
        display_opts.append('--' + opt[0])

    for arg in sys.argv:
        if arg in display_opts and arg not in ignore:
            return True

    return False


# TODO: With luck this can go away soon--packaging now supports adding the cwd
# to sys.path for running setup_hooks.  But it also needs to support adding
# packages_root.  Also, it currently does not support adding cwd/packages_root
# to sys.path for pre/post-command hooks, so that needs to be fixed.
def use_packages_root(config):
    """
    Adds the path specified by the 'packages_root' option, or the current path
    if 'packages_root' is not specified, to sys.path.  This is particularly
    useful, for example, to run setup_hooks or add custom commands that are in
    your package's source tree.
    """

    if 'files' in config and 'packages_root' in config['files']:
        root = config['files']['packages_root']
    else:
        root = ''

    if root not in sys.path:
        if root and sys.path[0] == '':
            sys.path.insert(1, root)
        else:
            sys.path.insert(0, root)

    # Reload the stsci namespace package in case any new paths can be added to
    # it from the new sys.path entry
    if 'stsci' in sys.modules:
        reload(sys.modules['stsci'])


def tag_svn_revision(config):
    """
    A setup_hook to add the SVN revision of the current working copy path to
    the package version string, but only if the version ends in .dev.

    For example, ``mypackage-1.0.dev`` becomes ``mypackage-1.0.dev1234``.  This
    is in accordance with the version string format standardized by PEP 386.

    This should be used as a replacement for the ``tag_svn_revision`` option to
    the egg_info command.  This hook is more compatible with
    packaging/distutils2, which does not include any VCS support.  This hook is
    also more flexible in that it turns the revision number on/off depending on
    the presence of ``.dev`` in the version string, so that it's not
    automatically added to the version in final releases.

    This hook does require the ``svnversion`` command to be available in order
    to work.  It does not examine the working copy metadata directly.
    """

    if 'metadata' in config and 'version' in config['metadata']:
        metadata = config['metadata']
        version = metadata['version']

        # Don't add an svn revision unless the version ends with .dev
        if not version.endswith('.dev'):
            return

        # First try to get the revision by checking for it in an existing
        # .version module
        package_dir = config.get('files', {}).get('packages_root', '')
        packages = config.get('files', {}).get('packages', '')
        packages = split_multiline(packages)
        rev = None
        for package in packages:
            version_py = package_uses_version_py(package_dir, package)
            if not version_py:
                continue
            try:
                mod = __import__(package + '.version',
                                 fromlist='__svn_revision__')
            except ImportError:
                mod = None
            if mod is not None and hasattr(mod, '__svn_revision__'):
                rev = mod.__svn_revision__
                break

        if rev is None:
            # A .version module didn't exist or was incomplete; try calling
            # svnversion directly
            rev = get_svn_version()

        if not rev:
            return
        if ':' in rev:
            rev, _ = rev.split(':', 1)
        while rev and rev[-1] not in string.digits:
            rev = rev[:-1]
        try:
            rev = int(rev)
        except (ValueError, TypeError):
            return

        metadata['version'] ='%s%d' % (version, rev)


def version_hook(function_name, package_dir, packages, name, version):
    """This command hook creates an version.py file in each package that
    requires it.  This is by determining if the package's __init__ tries
    to import or import from the version module.

    version.py will not be created in packages that don't use it.  It should
    only be used by the top-level package of the project.

    Don't use this function directly--instead use version_setup_hook() or
    version_pre_command_hook() which know how to retrieve the required metadata
    depending on the context they are run in.
    """

    # Strip any revision info from version; that will be handled separately
    if '-' in version:
        version = version.split('-', 1)[0]

    for package in packages:
        version_py = package_uses_version_py(package_dir, package)
        if not version_py:
            continue

        rev = get_svn_version()
        if (not rev or rev[0] not in string.digits and
            os.path.exists(version_py)):
            # If were unable to determine an SVN revision and the version.py
            # already exists, just update the __setup_datetime__ and leave the
            # rest of the file untouched
            update_setup_datetime(version_py)
            return
        elif rev is None:
            rev = 'Unable to determine SVN revision'

        svn_info = get_svn_info()

        # Wrap version, rev, and svn_info in str() to ensure that Python 2
        # unicode literals aren't written, which will break things in Python 3
        template_variables = {
                'hook_function': function_name,
                'name': name,
                'version': str(version),
                'svn_revision': str(rev),
                'svn_full_info': str(svn_info),
                'setup_datetime': datetime.datetime.now()
        }

        with open(version_py, 'w') as f:
            f.write(VERSION_PY_TEMPLATE % template_variables)


def version_setup_hook(config):
    if is_display_option(ignore=['--version']):
        return

    name = config['metadata'].get('name')
    version = config['metadata'].get('version', '0.0.0')
    package_dir = config.get('files', {}).get('packages_root', '')
    packages = config.get('files', {}).get('packages', '')

    packages = split_multiline(packages)

    version_hook(__name__ + '.version_setup_hook', package_dir, packages,
                 name, version)


def version_pre_command_hook(command_obj):
    """This command hook creates an version.py file in each package that
    requires it.  This is by determining if the package's __init__ tries
    to import or import from the version module.

    version.py will not be created in packages that don't use it.  It should
    only be used by the top-level package of the project.
    """

    if is_display_option():
        return

    package_dir = command_obj.distribution.package_dir.get('', '.')
    packages = command_obj.distribution.packages
    name = command_obj.distribution.metadata.name
    version = command_obj.distribution.metadata.version

    version_hook(__name__ + '.version_pre_command_hook',package_dir, packages,
                 name, version)


def version_post_command_hook(command_obj):
    """Cleans up a previously generated version.py in order to avoid
    clutter.

    Only removes the file if we're in an SVN working copy and the file is not
    already under version control.
    """

    package_dir = command_obj.distribution.package_dir.get('', '.')
    packages = command_obj.distribution.packages

    for package in packages:
        clean_version_py(package_dir, package)


def numpy_extension_hook(command_obj):
    """A distutils2 pre-command hook for the build_ext command needed for
    building extension modules that use NumPy.

    To use this hook, add 'numpy' to the list of include_dirs in setup.cfg
    section for an extension module.  This hook will replace 'numpy' with the
    necessary numpy header paths in the include_dirs option for that extension.

    Note: Although this function uses numpy, stsci.distutils does not depend on
    numpy.  It is up to the distribution that uses this hook to require numpy
    as a dependency.
    """

    command_name = command_obj.get_command_name()
    if command_name != 'build_ext':
        log.warn('%s is meant to be used with the build_ext command only; '
                 'it is not for use with the %s command.' %
                 (__name__, command_name))
    try:
        import numpy
    except ImportError:
        # It's virtually impossible to automatically install numpy through
        # setuptools; I've tried.  It's not pretty.
        # Besides, we don't want users complaining that our software doesn't
        # work just because numpy didn't build on their system.
        sys.stderr.write('\n\nNumpy is required to build this package.\n'
                         'Please install Numpy on your system first.\n\n')
        sys.exit(1)

    includes = [numpy.get_numarray_include(), numpy.get_include()]
    for extension in command_obj.extensions:
        if 'numpy' not in extension.include_dirs:
            continue
        idx = extension.include_dirs.index('numpy')
        for inc in includes:
            extension.include_dirs.insert(idx, inc)
        extension.include_dirs.remove('numpy')


def glob_data_files(command_obj):
    """A pre-command hook for the install_data command allowing wildcard
    patterns to be used in the data_files option.

    Also ensures that data files with relative paths as their targets are
    installed relative install_lib.
    """

    command_name = command_obj.get_command_name()
    if command_name != 'install_data':
        log.warn('%s is meant to be used with the install_data command only; '
                 'it is not for use with the %s command.' %
                 (__name__, command_name))

    data_files = command_obj.data_files

    for idx, val in enumerate(data_files[:]):
        if isinstance(val, basestring):
            # Support the rare, deprecated case where just a filename is given
            filenames = glob.glob(val)
            del data_files[idx]
            data_files.extend(filenames)
            continue

        dest, filenames = val
        filenames = sum((glob.glob(item) for item in filenames), [])
        data_files[idx] = (dest, filenames)

    # Ensure the correct install dir; this is the default behavior for
    # installing with distribute, but when using
    # --single-version-externally-managed we need to to tweak this
    install_cmd = command_obj.get_finalized_command('install')
    if command_obj.install_dir == install_cmd.install_data:
        install_lib_cmd = command_obj.get_finalized_command('install_lib')
        command_obj.install_dir = install_lib_cmd.install_dir
