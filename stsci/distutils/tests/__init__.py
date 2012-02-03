import os
import shutil
import subprocess
import sys
import tempfile

import nose


TESTPACKAGE_URL = ('https://svn.stsci.edu/svn/ssb/stsci_python/'
                   'stsci.distutils/trunk/stsci/distutils/tests/testpackage')
TESTPACKAGE_REV = '14811'  # The last known 'good' revision of this package


class StsciDistutilsTestCase(object):
    @classmethod
    def setup_class(cls):
        cls.wc_dir = tempfile.mkdtemp(prefix='stsci-distutils-test-')
        try:
            p = subprocess.Popen(['svn', '-r', TESTPACKAGE_REV,
                                  '--non-interactive', '--trust-server-cert',
                                  'checkout', TESTPACKAGE_URL, cls.wc_dir],
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
        except OSError, e:
            raise nose.SkipTest('svn unavailable to checkout out test '
                                'package: %s' % e)

        if p.wait() != 0:
            raise nose.SkipTest('svn failed to check out the test package: '
                                '%s; tests will not be able to run' %
                                p.stderr.read().decode('ascii'))

    @classmethod
    def teardown_class(cls):
        shutil.rmtree(cls.wc_dir)

    def setup(self):
        self.temp_dir = tempfile.mkdtemp(prefix='stsci-distutils-test-')
        self.package_dir = os.path.join(self.temp_dir, 'testpackage')
        shutil.copytree(self.wc_dir, self.package_dir)
        self.oldcwd = os.getcwd()
        os.chdir(self.package_dir)

        # We need to manually add the test package's path to the stsci
        # package's __path__ since it's already been imported.
        if 'stsci' in sys.modules:
            sys.modules['stsci'].__path__.insert(
                0, os.path.join(self.package_dir, 'stsci'))

    def teardown(self):
        os.chdir(self.oldcwd)
        # Remove stsci.testpackage from sys.modules so that it can be freshly
        # re-imported by the next test
        # if 'stsci.testpackage' in sys.modules:
        #    del sys.modules['stsci.testpackage']

        shutil.rmtree(self.temp_dir)

    def run_setup(self, args):
        # Most of the tests will start us out here, but just be sure...
        os.chdir(self.package_dir)
        p = subprocess.Popen([sys.executable, 'setup.py'] + args,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if p.wait() != 0:
            raise Exception('setup.py %s failed:\n%s' %
                            (' '.join(args), p.stderr.read().decode('ascii')))

