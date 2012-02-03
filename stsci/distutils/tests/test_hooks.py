import os

from datetime import datetime

from . import StsciDistutilsTestCase, TESTPACKAGE_REV
from .util import reload


VERSION = '0.1.dev' + TESTPACKAGE_REV


class TestHooks(StsciDistutilsTestCase):
    def setup(self):
        super(TestHooks, self).setup()
        # Build the package
        self.run_setup(['build'])
        self.run_setup(['sdist'])

    def test_version_with_rev(self):
        """Test that the version string contains the correct SVN revision."""

        import stsci.testpackage

        assert hasattr(stsci.testpackage, '__version__')
        assert stsci.testpackage.__version__ == VERSION

        assert hasattr(stsci.testpackage, '__svn_revision__')
        assert stsci.testpackage.__svn_revision__ == TESTPACKAGE_REV

        assert os.path.exists(
            os.path.join('dist', 'stsci.testpackage-%s.tar.gz' % VERSION))

    def test_setup_datetime(self):
        """
        Test that the setup datetime is present, and is updated by subsequent
        setup.py runs.
        """

        import stsci.testpackage

        assert hasattr(stsci.testpackage, '__setup_datetime__')
        prev = stsci.testpackage.__setup_datetime__
        now = datetime.now()
        # Rebuild
        self.run_setup(['build'])

        reload(stsci.testpackage.version)
        reload(stsci.testpackage)

        assert hasattr(stsci.testpackage, '__setup_datetime__')
        assert stsci.testpackage.__setup_datetime__ > now
        assert stsci.testpackage.__setup_datetime__ > prev
