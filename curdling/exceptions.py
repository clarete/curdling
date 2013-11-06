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


class CurdlingError(Exception):
    """Base exception for errors happening inside of curdling"""

    def __init__(self, message):
        super(CurdlingError, self).__init__(message)
        self.message = message


class ReportableError(CurdlingError):
    """Inform errors that happens inside of services

    This exception is raised by services that need to communicate that their
    run method failed. The only place I see this exception being caught is in
    the `services.Service._worker()` method. Although all the services might
    need to raise it.

    This exception should not be raised in any other scenarios.
    """


class UnknownURL(ReportableError):
    """Raised when the user feeds in the installer with an unknown URL"""


class TooManyRedirects(ReportableError):
    """Raised when a download exceeds the maximum number of redirects"""


class RequirementNotFound(ReportableError):
    """Raised when a requirement is not found by the finder"""


class UnpackingError(ReportableError):
    """Raised when a package can't be unpacked"""

class BuildError(ReportableError):
    """Raised when a package can't be built using the setup.py script"""


class BrokenDependency(ReportableError):
    """Raised to inform that a dependency couldn't be installed"""


class VersionConflict(ReportableError):
    """Raised when Maestro.best_version() can't find versions for all the requests"""


class NoSetupScriptFound(ReportableError):
    pass


class PackageNotInstalled(CurdlingError):
    pass
