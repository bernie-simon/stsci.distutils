import os

from ConfigParser import ConfigParser

import pkg_resources

from setuptools.command.easy_install import easy_install
from setuptools.package_index import PackageIndex


def distro_from_setup_cfg(filename):
    """
    Read a source checkout's distutils2 setup.cfg and create a Distribution for
    that checkout.

    filename can either be the path to the setup.cfg itself, or checkout
    directory containing the setup.cfg.
    """

    if os.path.isdir(filename):
        path = filename
        filename = os.path.join(filename, 'setup.cfg')
        if not os.path.exists(filename):
            return None
    else:
        path, basename = os.path.split(filename)
        if basename != 'setup.cfg':
            return None
    cfg = ConfigParser()
    cfg.read(filename)
    if not cfg.has_option('metadata', 'name'):
        return None
    name = cfg.get('metadata', 'name')
    if cfg.has_option('metadata', 'version'):
        version = cfg.get('metadata', 'version')
    else:
        version = None
    return pkg_resources.Distribution(
               location=path, project_name=name, version=version,
               precedence=pkg_resources.CHECKOUT_DIST)


class LocalSourcesPackageIndex(PackageIndex):
    """
    Like PackageIndex, but can also install packages from local source
    checkouts, the locations of which are added via add_find_links().

    Although PackageIndex supports installing for source distributions on the
    local filesystem, they must be in a tar/zip/etc.  This allows installing
    from an existing source checkout on the local filesystem.
    """

    def process_filename(self, fn, nested=False):
        PackageIndex.process_filename(self, fn, nested)
        dist = distro_from_setup_cfg(fn)
        if dist:
            self.add(dist)


class easier_install(easy_install):
    """
    Extension to the easy_install command that uses LocalSourcesPackageIndex as
    its default PackageIndex implementation.
    """

    create_index = LocalSourcesPackageIndex
