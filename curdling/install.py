from __future__ import absolute_import, print_function, unicode_literals
from functools import wraps

from .database import Database
from .index import PackageNotFound
from .maestro import Maestro
from .signal import SignalEmitter, Signal
from .util import logger

from .services.downloader import Downloader
from .services.curdler import Curdler
from .services.dependencer import Dependencer
from .services.installer import Installer
from .services.uploader import Uploader

import sys
import time

SUCCESS = 0

FAILURE = 1

PACKAGE_BLACKLIST = (
    'setuptools',
)


def only(func, field):
    @wraps(func)
    def wrapper(requester, requirement, **data):
        if data.get(field, False):
            return func(requester, requirement, **data)
    return wrapper


def mark(maestro, status):
    marklogger = logger('{0}.mark'.format(__name__))
    status_name = {
        Maestro.Status.PENDING: 'PENDING',
        Maestro.Status.RETRIEVED: 'RETRIEVED',
        Maestro.Status.BUILT: 'BUILT',
        Maestro.Status.INSTALLED: 'INSTALLED',
        Maestro.Status.FAILED: 'FAILED',
    }[status]

    def marker(requester, requirement, **data):
        marklogger.debug("%s, %s, %s", requirement, status_name, data)
        maestro.add_status(requirement, status)
        for field, value in tuple(data.items()):
            maestro.set_data(requirement, field, value)
    return marker


class Install(SignalEmitter):

    def __init__(self, conf):
        super(Install, self).__init__()

        self.conf = conf
        self.index = self.conf.get('index')
        self.database = Database()
        self.logger = logger(__name__)

        self.update = Signal()
        self.finished = Signal()

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

        # Not starting those guys since we don't actually have a lot to do here
        # right now. Check the `run` method, we'll call the installer and
        # uploader after making sure all the dependencies are installed.
        self.installer = Installer(**args)
        self.uploader = Uploader(**args)

        # Building the pipeline to [download -> compile -> install deps]
        self.downloader.connect('finished', only(self.curdler.queue, 'tarball'))
        self.downloader.connect('finished', only(self.dependencer.queue, 'wheel'))
        self.downloader.connect('finished', mark(self.maestro, Maestro.Status.RETRIEVED))
        self.downloader.connect('failed', mark(self.maestro, Maestro.Status.FAILED))
        self.curdler.connect('finished', self.dependencer.queue)
        self.curdler.connect('failed', mark(self.maestro, Maestro.Status.FAILED))
        self.dependencer.connect('dependency_found', self.request_install)
        self.dependencer.connect('built', mark(self.maestro, Maestro.Status.BUILT))
        self.dependencer.connect('failed', mark(self.maestro, Maestro.Status.FAILED))

        # Installer pipeline
        self.installer.connect('finished', mark(self.maestro, Maestro.Status.INSTALLED))

    def retrieve_and_build_stats(self):
        total = len(self.maestro.mapping.keys())
        retrieved = len(self.maestro.filter_by(Maestro.Status.RETRIEVED))
        built = len(self.maestro.filter_by(Maestro.Status.BUILT))
        failed = len(self.maestro.filter_by(Maestro.Status.FAILED))
        return total, retrieved, built, failed

    def run(self):
        # Wait until all the packages have the chance to be processed
        while True:
            total, retrieved, built, failed = self.retrieve_and_build_stats()
            self.emit('update', total, retrieved, built, failed)
            if total == built + failed:
                break
            time.sleep(0.5)

        # Let's not proceed on failures
        failed = self.maestro.filter_by(Maestro.Status.FAILED)
        if failed:
            self.emit('finished', self.maestro, failed)
            return FAILURE

        # We've got everything we need, let's rock it off!
        # self.run_installer()

        # Upload missing stuff that we couldn't find in curdling servers
        # if self.conf.get('upload'):
        #     self.run_uploader()
        self.emit('finished', self.maestro)
        return SUCCESS

    def run_installer(self):
        packages = self.maestro.filter_by(Maestro.Status.BUILT)
        for package_name in packages:
            _, requirement = self.maestro.best_version(package_name)
            self.installer.queue('main', package_name,
                wheel=self.maestro.get_data('wheel'))

        # If we don't have anything to do, we just bail
        if not packages:
            return SUCCESS

        # Installer UI
        self.installer.start()
        ui = InstallProgress(self, Maestro.Status.INSTALLED)
        while ui:
            time.sleep(0.5)
            ui.update()

        # We're the last service to write a progress bar so far, so we need to
        # append the newline right here. It will definitely go away (or move to
        # `run_uploader`) when changing the uploader to have a nice UI
        sys.stdout.write('\n')

        failed = self.maestro.filter_by(Maestro.Status.FAILED)
        if failed:
            self.report(failed)
            return FAILURE

        return SUCCESS

    def run_uploader(self):
        failures = self.downloader.get_servers_to_update()
        if not failures:
            return SUCCESS

        uploader = self.uploader.start()
        for server, package_names in failures.items():
            for package_name in package_names:
                _, version = self.maestro.best_version(package_name)
                uploader.queue('main', package_name,
                    path=version['data'].get('path'), server=server)
        uploader.join()
        return SUCCESS

    def request_install(self, requester, requirement, **data):
        # If it's a blacklisted requirement, we should cowardly refuse to
        # install
        for blacklisted in PACKAGE_BLACKLIST:
            if requirement.startswith(blacklisted):
                self.logger.info(
                    "Cowardly refusing to install blacklisted "
                    "requirement `%s'", requirement)
                return False

        # Well, the requirement is installed, let's just bail
        if not self.conf.get('force') and self.database.check_installed(requirement):
            return True

        # Let's tell the maestro we have a new challenger
        self.maestro.file_requirement(
            requirement, dependency_of=data.get('dependency_of'))

        # Looking for built packages
        try:
            wheel = self.index.get("{0};whl".format(requirement))
            self.maestro.set_data(requirement, 'wheel', wheel)
            self.dependencer.queue(requester, requirement, wheel=wheel)
            return False
        except PackageNotFound:
            pass

        # Looking for downloaded packages. If there's packages of any of the
        # following distributions, we'll just build the wheel
        try:
            tarball = self.index.get("{0};~whl".format(requirement))
            self.maestro.set_data(requirement, 'tarball', tarball)
            self.maestro.set_status(requirement, Maestro.Status.RETRIEVED)
            self.curdler.queue(requester, requirement, tarball=tarball)
            return False
        except PackageNotFound:
            pass

        # Nops, we really don't have the package
        self.downloader.queue(requester, requirement, **data)
        return False
