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

from . import exceptions
from .database import Database
from .util import logger, parse_requirement


class Uninstall(object):

    def __init__(self, conf):
        self.conf = conf
        self.packages = []
        self.logger = logger(__name__)

    def report(self):
        pass

    def request_uninstall(self, requirement):
        self.packages.append(parse_requirement(requirement).name)

    def run(self):
        for package in self.packages:
            self.logger.info("Removing package %s", package)

            try:
                Database.uninstall(package)
            except exceptions.PackageNotInstalled:
                self.logger.error("Package %s does not exist, skipping", package)
