"""Functions for getting and saving SVN info for distribution."""


from __future__ import with_statement

import os
import subprocess

from stsci.distutils.astutils import ImportVisitor, walk


def get_svn_rev(path='.'):
    """Uses `svnversion` to get just the latest revision at the given path."""

    try:
        pipe = subprocess.Popen(['svnversion', path], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
    except OSError:
        return None

    if pipe.wait() != 0:
        return None

    return pipe.stdout.read().decode('ascii').strip()


def get_svn_info(path='.'):
    """Uses `svn info` to get the full information about the working copy at
    the given path.
    """

    path = os.path.abspath(path)

    try:
        pipe = subprocess.Popen(['svn', 'info', path], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        # stderr is redirected in order to squelch it.  Later Python versions
        # have subprocess.DEVNULL for this purpose, but it's not available in
        # 2.5
    except OSError:
        return 'unknown'

    if pipe.wait() != 0:
        return 'unknown'

    lines = []
    for line in pipe.stdout.readlines():
        line = line.decode('ascii').strip()
        if not line:
            continue
        if line.startswith('Path:'):
            line = 'Path: %s' % os.path.basename(path)
        lines.append(line)

    if not lines:
        return 'unknown'

    return '\n'.join(lines)


def write_svn_info(path='.', filename='version.py', append=False):
    rev = get_svn_rev(path)

    # if we are unable to determine the revision, we default to leaving the
    # existing revision file unchanged.  Otherwise, we fill it in with whatever
    # we have

    if rev is None:
        if os.path.exists(filename):
            return
        rev = 'Unable to determine SVN revision'
    else:
        if rev in ('exported', 'unknown') and os.path.exists(filename):
            return

    info = get_svn_info(path)

    with open(filename, 'a' if append else 'w') as f:
        f.write('__svn_revision__ = %r\n' % rev)
        f.write('__svn_full_info__ = """\n%s\n"""\n\n' % info)
