from __future__ import absolute_import, print_function, unicode_literals
from functools import wraps

from .database import Database
from .index import PackageNotFound
from .maestro import Maestro
from .signal import SignalEmitter, Signal
from .util import logger, is_url

from .services.downloader import Finder, Downloader
from .services.curdler import Curdler
from .services.dependencer import Dependencer
from .services.installer import Installer
from .services.uploader import Uploader

import os
import time

SUCCESS = 0

FAILURE = 1

PACKAGE_BLACKLIST = (
    'setuptools',
)


def only(func, field):
    @wraps(func)
    def wrapper(requester, **data):
        if data.get(field, False):
            return func(requester, **data)
    return wrapper


def mark(maestro, status):
    marklogger = logger('{0}.mark'.format(__name__))
    status_name = {
        Maestro.Status.PENDING: 'PENDING',
        Maestro.Status.FOUND: 'FOUND',
        Maestro.Status.RETRIEVED: 'RETRIEVED',
        Maestro.Status.BUILT: 'BUILT',
        Maestro.Status.CHECKED: 'CHECKED',
        Maestro.Status.INSTALLED: 'INSTALLED',
        Maestro.Status.FAILED: 'FAILED',
    }[status]

    def marker(requester, **data):
        requirement = data['requirement']
        marklogger.debug("%s, %s, %s", requirement, status_name, data)
        maestro.add_status(requirement, status)
        for field, value in tuple(data.items()):
            if field != 'requirement':
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

        # General params for all the services
        args = self.conf
        args.update({
            'env': self,
            'index': self.index,
            'conf': self.conf,
        })

        self.maestro = Maestro()
        self.finder = Finder(**args)
        self.downloader = Downloader(**args)
        self.curdler = Curdler(**args)
        self.dependencer = Dependencer(**args)

        # Not starting those guys since we don't actually have a lot to do here
        # right now. Check the `run` method, we'll call the installer and
        # uploader after making sure all the dependencies are installed.
        self.installer = Installer(**args)
        self.uploader = Uploader(**args)

    def pipeline(self):
        # Building the pipeline to [find -> download -> build -> find deps]
        self.finder.connect('finished', self.downloader.queue)
        self.downloader.connect('finished', only(self.curdler.queue, 'tarball'))
        self.downloader.connect('finished', only(self.dependencer.queue, 'wheel'))
        self.curdler.connect('finished', self.dependencer.queue)
        self.dependencer.connect('dependency_found', self.feed)

    def start(self):
        self.finder.start()
        self.downloader.start()
        self.curdler.start()
        self.dependencer.start()

    def set_url(self, data):
        requirement = data['requirement']
        if is_url(requirement):
            data['url'] = requirement
            return True
        return False

    def set_tarball(self, data):
        # Looking for downloaded packages. If there's packages of any of the
        # following distributions, we'll just build the wheel
        try:
            data['tarball'] = \
                self.index.get("{0};~whl".format(data['requirement']))
            return True
        except PackageNotFound:
            return False

    def set_wheel(self, data):
        try:
            data['wheel'] = \
                self.index.get("{0};whl".format(data['requirement']))
            return True
        except PackageNotFound:
            return False

    def feed(self, requester, **data):
        service = None
        if self.set_wheel(data):
            service = self.dependencer
        elif self.set_tarball(data):
            service = self.curdler
        elif self.set_url(data):
            service = self.downloader
        else:
            service = self.finder

        service.queue(requester, **data)

    def retrieve_and_build_stats(self):
        total = len(self.maestro.mapping.keys())
        pending = len(self.maestro.filter_by(Maestro.Status.PENDING))
        found = len(self.maestro.filter_by(Maestro.Status.FOUND))
        retrieved = len(self.maestro.filter_by(Maestro.Status.RETRIEVED))
        checked = len(self.maestro.filter_by(Maestro.Status.CHECKED))
        failed = len(self.maestro.filter_by(Maestro.Status.FAILED))
        return total, pending, found, retrieved, checked, failed

    def run(self):
        # Wait until all the packages have the chance to be processed
        while True:
            total, pending, found, retrieved, built, failed = self.retrieve_and_build_stats()
            self.emit('update', total, retrieved, built, failed)
            # if total == pending + found + retrieved + built + failed:
            #     break
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
        packages = self.maestro.filter_by(Maestro.Status.CHECKED)
        for package_name in packages:
            _, requirement = self.maestro.best_version(package_name)
            self.installer.queue('main', package_name,
                wheel=self.maestro.get_data(requirement, 'wheel'))

        # If we don't have anything to do, we just bail
        if not packages:
            self.emit('finished')
            return SUCCESS

        # Installer UI
        self.installer.start()
        while True:
            total = len(self.maestro.filter_by(Maestro.Status.CHECKED))
            installed = len(self.maestro.filter_by(Maestro.Status.INSTALLED))

        ui = InstallProgress(self, Maestro.Status.INSTALLED)
        while ui:
            time.sleep(0.5)
            ui.update()

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
