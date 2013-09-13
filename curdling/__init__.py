from __future__ import unicode_literals, print_function, absolute_import
from collections import namedtuple
from functools import wraps
from distlib.database import DistributionPath
from distlib.util import parse_requirement
from pip.commands.uninstall import UninstallCommand

from .logging import Logger, ReportableError
from .index import PackageNotFound
from .maestro import Maestro

from .download import Downloader
from .wheelhouse import Curdler
from .dependency import Dependencer
from .installer import Installer
from .uploader import Uploader

import re

PACKAGE_BLACKLIST = (
    'setuptools',
)


def only(func, pattern):
    @wraps(func)
    def wrapper(requester, package, **data):
        if re.match(pattern, data.get('path', '')):
            return func(requester, package, **data)
    return wrapper


class Env(object):
    def __init__(self, conf):
        self.conf = conf
        self.index = self.conf.get('index')
        self.logger = Logger('main', conf.get('log_level'))

    def start_services(self):
        # General params for all the services
        args = self.conf
        args.update({
            'env': self,
            'index': self.index,
            'conf': self.conf,
        })

        self.maestro = Maestro()
        self.downloader = Downloader(**args).start()
        self.curdler = Curdler(**args).start()
        self.dependencer = Dependencer(**args).start()
        self.installer = Installer(**args).start()
        self.uploader = Uploader(**args).start()

        # Building the pipeline
        self.downloader.connect('finished', only(self.curdler.queue, r'^(?!.*\.whl$)'))
        self.downloader.connect('finished', only(self.dependencer.queue, r'.*\.whl$'))
        self.curdler.connect('finished', self.dependencer.queue)
        self.dependencer.connect('dependency_found', self.downloader.queue)

    def wait(self):
        import time
        while True:
            time.sleep(0.5)

    def shutdown(self):
        self.logger.level(2, "*table flip*")
        return {}

    def check_installed(self, package):
        return DistributionPath().get_distribution(
            parse_requirement(package).name.replace('_', '-')) is not None

    def request_install(self, requirement, requester='main', **data):
        # If it's a blacklisted requirement, we should cowardly refuse to
        # install
        for blacklisted in PACKAGE_BLACKLIST:
            if requirement.startswith(blacklisted):
                self.logger.level(2,
                    "Cowardly refusing to install blacklisted "
                    "requirement `%s'", requirement)
                return False

        # # Well, the package is installed, let's just bail
        # if self.check_installed(requirement):
        #     return True

        # # Looking for built packages
        # try:
        #     path = self.index.get("{0};whl".format(requirement))
        #     data.update({'path': path})
        #     self.services['install'].queue(requirement, requester, **data)
        #     return False
        # except PackageNotFound:
        #     pass

        # # Looking for downloaded packages. If there's packages of any of the
        # # following distributions, we'll just build the wheel
        # try:
        #     path = self.index.get("{0};~whl".format(requirement))
        #     data.update({'path': path})
        #     self.services['curdling'].queue(requirement, requester, **data)
        #     return False
        # except PackageNotFound:
        #     pass

        # Nops, we really don't have the package
        self.downloader.queue(requester, requirement, **data)
        return False

    def uninstall(self, package):
        # We just overwrite the constructor here cause it's not actualy useful
        # unless you're creating another command, not calling as a library.
        class Uninstall(UninstallCommand):
            def __init__(self):
                pass

        # Just creating an object that pretends to be the option container for
        # the `run()` method.
        opts = namedtuple('Options', 'yes requirements')
        Uninstall().run(opts(yes=True, requirements=[]), [package])
