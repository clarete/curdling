# Curdling - Concurrent package manager for Python
# Copyright (C) 2013  Lincoln Clarete <lincoln@clarete.li>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

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
