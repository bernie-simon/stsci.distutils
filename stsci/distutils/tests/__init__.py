import shutil
import subprocess
import tempfile

import nose


TESTPACKAGE_URL = 'https://svn.stsci.edu/svn/ssb/stsci_python/stsci.distutils/'
                  'trunk/stsci/distutils/tests/testpackage'
TESTPACKAGE_REV = '14705'  # The last known 'good' revision of this package


class StsciDistutilsTestCase(object):
    def setup_class(self):
        self.wc_dir = tempfile.mkdtemp(prefix='stsci-distutils-test-')
        try:
            p = subprocess.Popen(['svn', '-r', TESTPACKAGE_REV,
                                  '--non-interactive', '--trust-server-cert',
                                  TESTPACKAGE_URL, self.wc_dir],
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
        except OSError, e:
            raise nose.SkipTest('svn unavailable to checkout out test '
                                'package: %s' % e)

        if p.wait() != 0:
            raise nose.SkipTest('svn failed to check out the test package: '
                                '%s; tests will not be able to run')

    def teardown_class(self):
        shutil.rmtree(self.wc_dir)

    def setup(self):
        self.temp_dir = tempfile.mkdtemp(prefix='stsci-distutils-test-')

    def teardown(self):
        shutil.rmtree(self.temp_dir)
