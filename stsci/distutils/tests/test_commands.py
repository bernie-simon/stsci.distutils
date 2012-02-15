from __future__ import with_statement


import os

from . import StsciDistutilsTestCase
from .util import get_compiler_command, open_config


class TestCommands(StsciDistutilsTestCase):
    def test_build_optional_ext(self):
        # The test extension in the test package is already configured to be
        # "optional" by default--we'll do one test build to make sure that goes
        # smoothly
        compiler_cmd = get_compiler_command()

        stdout, _, exit_code = self.run_setup('build')

        # The last line of output should be from a successful compiler command
        assert exit_code == 0
        assert stdout.splitlines()[-1].split()[0] == compiler_cmd

        # Now let's try breaking the build
        with open(os.path.join('src', 'testext.c'), 'a') as f:
            f.write('1/0')

        # We leave off the exit status from the compiler--in most cases it will
        # say "exit status 1" but that can't be guaranteed for all compilers
        msg = ('building optional extension "stsci.testpackage.testext" '
               'failed: command \'%s\' failed with exit status' % compiler_cmd)
        _, stderr, exit_code = self.run_setup('build', '--force')
        assert exit_code == 0
        assert stderr.splitlines()[-1].startswith(msg)

        # Test a custom fail message
        with open_config('setup.cfg') as cfg:
            cfg.set('extension=stsci.testpackage.testext', 'fail_message',
                    'Custom fail message: %message')

        msg = ("Custom fail message: command '%s' failed with exit status" %
               compiler_cmd)
        _, stderr, exit_code = self.run_setup('build', '--force')
        assert exit_code == 0
        assert stderr.splitlines()[-1].startswith(msg)

        # Finally, make sure the extension is *not* treated as optional if not
        # marked as such in the config
        with open_config('setup.cfg') as cfg:
            cfg.remove_option('extension=stsci.testpackage.testext',
                              'optional')

        msg = "error: command '%s' failed with exit status" % compiler_cmd
        _, stderr, exit_code = self.run_setup('build', '--force')
        assert exit_code != 0
        assert stderr.splitlines()[-1].startswith(msg)
