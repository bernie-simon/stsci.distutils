import glob
import os
import shlex
import shutil
import tarfile

from ConfigParser import ConfigParser
from datetime import datetime
from distutils.ccompiler import new_compiler, customize_compiler
from setuptools import Distribution

from . import StsciDistutilsTestCase, TESTPACKAGE_REV
from .util import reload


VERSION = '0.1.dev' + TESTPACKAGE_REV


class TestHooks(StsciDistutilsTestCase):
    def setup(self):
        super(TestHooks, self).setup()

    def test_setup_py_version(self):
        """
        Test that the `./setupy.py --version` command returns the correct
        value without balking.
        """

        stdout, _ = self.run_setup('--version')
        assert stdout == VERSION

    def test_version_with_rev(self):
        """Test that the version string contains the correct SVN revision."""

        # Build the package
        self.run_setup('build')
        self.run_setup('sdist')

        import stsci.testpackage

        assert hasattr(stsci.testpackage, '__version__')
        assert stsci.testpackage.__version__ == VERSION

        assert hasattr(stsci.testpackage, '__svn_revision__')
        assert stsci.testpackage.__svn_revision__ == TESTPACKAGE_REV

        assert os.path.exists(
            os.path.join('dist', 'stsci.testpackage-%s.tar.gz' % VERSION))

    def test_release_version(self):
        """
        Ensure that the SVN revision is not appended to release versions
        (i.e. not ending with '.dev'.
        """

        cfg = ConfigParser()
        cfg.read('setup.cfg')
        cfg.set('metadata', 'version', '0.1')
        with open('setup.cfg', 'w') as fp:
            cfg.write(fp)

        stdout, _ = self.run_setup('--version')
        assert stdout == '0.1'

    def test_inline_svn_update(self):
        """Test version.py's capability of updating the SVN info at runtime."""

        self.run_setup('build')

        import stsci.testpackage

        assert hasattr(stsci.testpackage, '__svn_revision__')
        assert stsci.testpackage.__svn_revision__ == TESTPACKAGE_REV

        with open('TEST', 'w') as f:
            # Create an empty file
            pass

        self.run_svn('add', 'TEST')
        # The working copy has been modified, so now svnversion (which is used
        # to generate __svn_revision__) should be the revision + 'M'
        reload(stsci.testpackage.version)
        reload(stsci.testpackage)

        assert stsci.testpackage.__svn_revision__ == TESTPACKAGE_REV + 'M'

    def test_setup_datetime(self):
        """
        Test that the setup datetime is present, and is updated by subsequent
        setup.py runs.
        """

        # Build the package
        self.run_setup('build')

        import stsci.testpackage

        assert hasattr(stsci.testpackage, '__setup_datetime__')
        prev = stsci.testpackage.__setup_datetime__
        now = datetime.now()
        # Rebuild
        self.run_setup('build')

        reload(stsci.testpackage.version)
        reload(stsci.testpackage)

        assert hasattr(stsci.testpackage, '__setup_datetime__')
        assert stsci.testpackage.__setup_datetime__ > now
        assert stsci.testpackage.__setup_datetime__ > prev

    def test_numpy_extension_hook(self):
        """Test basic functionality of the Numpy extension hook."""

        compiler = new_compiler()
        customize_compiler(compiler)
        compiler_exe = compiler.compiler[0]

        stdout, _ = self.run_setup('build')
        for line in stdout.splitlines():
            args = shlex.split(line)
            if args[0] != compiler_exe:
                continue

            # The first output from the compiler should be an attempt to
            # compile a c file to an object, so that should include all the
            # include paths.  This is of course not universally true, but it
            # should hold true for this test case
            for path in [numpy.get_include(), numpy.get_numarray_include()]:
                assert '-I' + path in args
            break

        # And for the heck of it, let's ensure that this doesn't happen if
        # 'numpy' is not listed in include_dirs
        cfg = ConfigParser()
        cfg.read('setup.cfg')
        cfg.remove_option('extension=stsci.testpackage.testext',
                          'include_dirs')
        with open('setup.cfg', 'w') as fp:
            cfg.write(fp)

        shutil.rmtree('build')

        stdout, _ = self.run_setup('build')
        for line in stdout.splitlines():
            args = shlex.split(line)
            if args[0] != compiler_exe:
                continue
            for path in [numpy.get_include(), numpy.get_numarray_include()]:
                assert '-I' + path not in args

    def test_glob_data_files(self):
        """
        Test the glob_data_files hook by ensuring that all the correct data
        files are included in the source distribution, and that they are
        installed to the correct location in the package.
        """

        data_files = os.path.join('stsci', 'testpackage', 'data_files')

        # First test the source distribution
        self.run_setup('sdist')

        # There can be only one
        tf = tarfile.open(glob.glob(os.path.join('dist', '*.tar.gz'))[0])

        # Tarfiles created by sdist kindly place all contents in a top-level
        # directory with the same name as the file minus extension, so as to
        # kindly not bomb you when you extract it.  But we don't care about
        # that top level directory
        names = [os.sep.join(p.split(os.sep)[1:]) for p in tf.getnames()]

        # Sdists should place the data_files at the root, just like in the
        # normal source layout; even files that aren't normally installed
        # should be included
        for filename in ['a.txt', 'b.txt', 'c.rst']:
            assert os.path.join('data_files', filename) in names

        # Now we test that data_files go to the right place in various install
        # schemes
        def get_install_lib(args):
            # This helper uses the distutils/setuptools machinery to determine
            # where a command will install files based on the arguments passed
            # to setup.py
            dist = Distribution({'script_args': args})
            dist.parse_command_line()
            install_cmd = dist.get_command_obj('install')
            install_cmd.ensure_finalized()
            return install_cmd.install_lib

        def test_install_scheme(args):
            # This general code should work to test the files in a variety of
            # install schemes depending on args
            if os.path.exists('temp'):
                shutil.rmtree('temp')
            install_lib = get_install_lib(args)
            os.makedirs(install_lib)
            old_pythonpath = os.environ.get('PYTHONPATH')
            # For a setuptools/easy_install-stype install to an alternate
            # prefix we have to have the new install dir on the PYTHONPATH or
            # easy_install will balk
            os.environ['PYTHONPATH'] = (
                install_lib + os.pathsep +
                (old_pythonpath if old_pythonpath else ''))

            try:
                self.run_setup(*(args + ['--record=installed.txt']))
            finally:
                if old_pythonpath is not None:
                    os.environ['PYTHONPATH'] = old_pythonpath

            install_lib = os.path.abspath(install_lib)
            with open('installed.txt') as f:
                for line in f:
                    if line.endswith('/a.txt'):
                        assert line == os.path.join(install_lib, data_files,
                                                    'a.txt')
                    elif line.endswith('/b.txt'):
                        assert line == os.path.join(install_lib, data_files,
                                                    'b.txt')
                    elif line.endswith('/c.rst'):
                        assert line != os.path.join(install_lib, data_files,
                                                'c.rst')

        test_install_scheme(['install', '--prefix=temp'])
        test_install_scheme(['install', '--root=temp'])
        test_install_scheme(['install', '--install-lib=temp'])
