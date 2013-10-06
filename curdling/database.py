from __future__ import absolute_import, print_function, unicode_literals
from . import util, exceptions
from distlib.database import DistributionPath

import os


class Database(object):

    @classmethod
    def check_installed(cls, requirement):
        path = DistributionPath(include_egg=True)
        package_name = util.parse_requirement(requirement).name
        return path.get_distribution(package_name) is not None

    @classmethod
    def uninstall(self, requirement):
        # Currently we assume the distribution path contains only the last
        # version installed
        package_name = util.parse_requirement(requirement).name
        distribution = DistributionPath(include_egg=True).get_distribution(
            package_name)

        # Oh distlib, if the distribution doesn't exist, we'll get None here
        if not distribution:
            raise exceptions.PackageNotInstalled(
                "There's no package named {0} installed in your environment".format(
                    package_name))

        # Distlib is not that smart about paths for files inside of
        # distributions too, so to find the full path to the distribution
        # files, we'll have to concatenate them to this base path manually :/
        base = os.path.dirname(distribution.path)

        # Let's now remove all the installed files
        for path, hash_, size in distribution.list_installed_files():
            os.unlink(os.path.join(base, path))

        # Removing the package directories
        os.rmdir(distribution.path)
