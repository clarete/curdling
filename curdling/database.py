from __future__ import absolute_import, print_function, unicode_literals
from collections import namedtuple
from distlib.database import DistributionPath
from distlib.util import parse_requirement
from pip.commands.uninstall import UninstallCommand


# We just overwrite the constructor here cause it's not actualy useful
# unless you're creating another command, not calling as a library.
class Uninstall(UninstallCommand):
    def __init__(self):
        pass


class Database(object):

    @classmethod
    def check_installed(cls, package):
        return DistributionPath().get_distribution(
            parse_requirement(package).name.replace('_', '-')) is not None

    @classmethod
    def uninstall(self, package):
        # Just creating an object that pretends to be the option container for
        # the `run()` method.
        opts = namedtuple('Options', 'yes requirements')
        Uninstall().run(opts(yes=True, requirements=[]), [package])
