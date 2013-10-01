from __future__ import absolute_import, print_function, unicode_literals


class CurdlingError(Exception):
    """Base exception for errors happening inside of curdling"""


class ReportableError(CurdlingError):
    """Inform errors that happens inside of services

    This exception is raised by services that need to communicate that their
    run method failed. The only place I see this exception being caught is in
    the `services.Service._worker()` method. Although all the services might
    need to raise it.

    This exception should not be raised in any other scenarios.
    """


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
