#!/usr/bin/env python

try:
    from setuptools import setup
except ImportError:
    from distribute_setup import use_setuptools
    use_setuptools()
    from setuptools import setup

import sys

from pkg_resources import working_set, get_distribution, Requirement


# If stsci.distutils is being used to install another package in the stsci
# namespace package, we may need to first re-import the stsci package so that
# all the entries (including the current path) are added to stsci.__path__
# Deleting 'stsci' from sys.modules will force such a re-import.
if 'stsci' in sys.modules:
    del sys.modules['stsci']


# This is a workaround for http://bugs.python.org/setuptools/issue20; most
# packages that have this package as a setup-requirement also have d2to1 as
# a setup-requirement, which can lead to bugginess.
# See also http://mail.python.org/pipermail/distutils-sig/2011-May/017812.html
# for a description of the problem (in my example, package_A is d2to1 and
# package_B is stsci.distutils).
# This issue was fixed in distribute 0.6.17, but leaving in support for older
# versions for now.
requirement = Requirement.parse('distribute<0.6.19')
try:
    has_issue205 = get_distribution('distribute') in requirement
except:
    has_issue205 = False

if has_issue205:
    save_entries = working_set.entries[:]
    save_entry_keys = working_set.entry_keys.copy()
    save_by_key = working_set.by_key.copy()

try:
    setup(
        setup_requires=['d2to1>=0.2.5'],
        namespace_packages=['stsci'], packages=['stsci'],
        dependency_links=['http://stsdas.stsci.edu/download/packages'],
        d2to1=True,
        use_2to3=True,
        zip_safe=False,
    )
finally:
    if has_issue205:
        working_set.entries = save_entries
        working_set.entry_keys = save_entry_keys
        working_set.by_key = save_by_key
