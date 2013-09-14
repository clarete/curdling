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
import time

SUCCESS = 0

FAILURE = 1

PACKAGE_BLACKLIST = (
    'setuptools',
)


def only(func, pattern):
    @wraps(func)
    def wrapper(requester, package, **data):
        if re.match(pattern, data.get('path', '')):
            return func(requester, package, **data)
    return wrapper


def mark(func):
    @wraps(func)
    def wrapper(requester, package, **data):
        return func(package, data['path'])
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

        # Building the pipeline
        self.downloader.connect('finished', only(self.curdler.queue, r'^(?!.*\.whl$)'))
        self.downloader.connect('finished', only(self.dependencer.queue, r'.*\.whl$'))
        self.downloader.connect('failed', mark(self.maestro.mark_failed))
        self.curdler.connect('finished', self.dependencer.queue)
        self.dependencer.connect('dependency_found', self.request_install)
        self.dependencer.connect('built', mark(self.maestro.mark_built))

        # Not starting those guys since we don't actually have a lot to do here
        # right now. Check the `run` method, we'll call the installer and
        # uploader after making sure all the dependencies are installed.
        self.installer = Installer(**args)
        self.uploader = Uploader(**args)

    def report(self):
        self.logger.level(0, 'Is there cheese in your rug?')
        for package in self.maestro.failed:
            path = self.maestro.mapping[package].values()[0]
            self.logger.level(0, " * %s", path)

    def run(self):
        while self.maestro.pending_packages:
            # print(self.maestro.built)
            time.sleep(0.5)

        if self.maestro.failed:
            self.report()
            return FAILURE

        # We've got everything we need, let's rock it off!
        self.run_installer()

        # Upload missing stuff that we couldn't find in curdling servers
        if self.conf.get('upload'):
            self.run_uploader()
        return SUCCESS

    def run_installer(self):
        self.installer.start()
        for package, versions in self.maestro.mapping.items():
            path = versions.values()[0]
            self.installer.queue('main', package, path=path)
        self.installer.join()

    def run_uploader(self):
        failures = self.downloader.get_servers_to_update()
        if not failures:
            return

        uploader = self.uploader.start()
        for server, packages in failures.items():
            for package in packages:
                path = self.maestro.mapping[package].values()[0]
                uploader.queue('main', package, path=path, server=server)
        uploader.join()

    def check_installed(self, package):
        return DistributionPath().get_distribution(
            parse_requirement(package).name.replace('_', '-')) is not None

    def request_install(self, requester, package, **data):
        # If it's a blacklisted requirement, we should cowardly refuse to
        # install
        for blacklisted in PACKAGE_BLACKLIST:
            if package.startswith(blacklisted):
                self.logger.level(2,
                    "Cowardly refusing to install blacklisted "
                    "requirement `%s'", package)
                return False

        # # Well, the package is installed, let's just bail
        # if self.check_installed(requirement):
        #     return True

        # Let's tell the maestro we have a new challenger
        self.maestro.file_package(package, dependency_of=data.get('dependency_of'))

        # Looking for built packages
        try:
            path = self.index.get("{0};whl".format(package))
            self.dependencer.queue(requester, package, path=path)
            return False
        except PackageNotFound:
            pass

        # Looking for downloaded packages. If there's packages of any of the
        # following distributions, we'll just build the wheel
        try:
            path = self.index.get("{0};~whl".format(package))
            self.curdler.queue(requester, package, path=path)
            return False
        except PackageNotFound:
            pass

        # Nops, we really don't have the package
        self.downloader.queue(requester, package, **data)
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
