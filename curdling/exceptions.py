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


class PackageNotInstalled(CurdlingError):
    pass
