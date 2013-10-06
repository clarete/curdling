from __future__ import absolute_import, print_function, unicode_literals
from functools import wraps

from .index import PackageNotFound
from .maestro import Maestro
from .database import Database
from .util import logger, spaces

from .services.downloader import Downloader
from .services.curdler import Curdler
from .services.dependencer import Dependencer
from .services.installer import Installer
from .services.uploader import Uploader

import re
import sys
import time

SUCCESS = 0

FAILURE = 1

PACKAGE_BLACKLIST = (
    'setuptools',
)


def only(func, pattern):
    @wraps(func)
    def wrapper(requester, requirement, **data):
        if re.match(pattern, data.get('path', '')):
            return func(requester, requirement, **data)
    return wrapper


def mark(maestro, set_name):
    def marker(requester, requirement, **data):
        return maestro.mark(set_name, requirement, data)
    return marker


class Install(object):

    def __init__(self, conf):
        self.conf = conf
        self.index = self.conf.get('index')
        self.database = Database()
        self.logger = logger(__name__)

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
        self.downloader.connect('finished', only(self.curdler.queue, r'^(?!.*\.whl$)'))
        self.downloader.connect('finished', only(self.dependencer.queue, r'.*\.whl$'))
        self.downloader.connect('finished', mark(self.maestro, 'retrieved'))
        self.downloader.connect('failed', mark(self.maestro, 'failed'))
        self.curdler.connect('finished', self.dependencer.queue)
        self.curdler.connect('failed', mark(self.maestro, 'failed'))
        self.dependencer.connect('dependency_found', self.request_install)
        self.dependencer.connect('built', mark(self.maestro, 'built'))
        self.dependencer.connect('failed', mark(self.maestro, 'failed'))

        # Installer pipeline
        self.installer.connect('finished', mark(self.maestro, 'installed'))

    def report(self):
        if self.maestro.failed:
            print('\nSome milk was spilled in the process:')
        for package_name in self.maestro.failed:
            print(' * {0}: '.format(package_name))
            for version in self.maestro.best_version(package_name):
                exception = version[1]['data']['exception']
                print('   {0}:\n{1}'.format(
                    exception.__class__.__name__,
                    spaces(5, str(exception))))

    def run(self):
        ui = RetrieveAndBuildProgress(self, 'built')
        while ui:
            time.sleep(0.5)
            ui.update()

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
        if not self.maestro.mapping:
            return SUCCESS
        else:
            self.installer.start()

        # If there's packages to install, let's queue them.
        for package_name in self.maestro.mapping:
            _, version = self.maestro.best_version(package_name)
            self.installer.queue('main', package_name,
                path=version['data']['path'])

        ui = InstallProgress(self, 'installed')
        while ui:
            time.sleep(0.5)
            ui.update()

        # We're the last service to write a progress bar so far, so we need to
        # append the newline right here. It will definitely go away (or move to
        # `run_uploader`) when changing the uploader to have a nice UI
        sys.stdout.write('\n')

        if self.maestro.failed:
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

        # We shouldn't queue the same requirement twice
        if not self.maestro.should_queue(requirement):
            return False

        # Let's tell the maestro we have a new challenger
        self.maestro.file_requirement(
            requirement, dependency_of=data.get('dependency_of'))

        # Looking for built packages
        try:
            path = self.index.get("{0};whl".format(requirement))
            self.dependencer.queue(requester, requirement, path=path)
            self.maestro.mark('retrieved', requirement, 'whl')
            return False
        except PackageNotFound:
            pass

        # Looking for downloaded packages. If there's packages of any of the
        # following distributions, we'll just build the wheel
        try:
            path = self.index.get("{0};~whl".format(requirement))
            self.curdler.queue(requester, requirement, path=path)
            self.maestro.mark('retrieved', requirement, 'compressed')
            return False
        except PackageNotFound:
            pass

        # Nops, we really don't have the package
        self.downloader.queue(requester, requirement, **data)
        return False


class Progress(object):

    def __init__(self, install, watch):
        self.install = install
        self.watch = watch

    def __nonzero__(self):
        return bool(self.install.maestro.pending(self.watch))

    def processed_packages(self):
        total = len(self.install.maestro.mapping)
        pending = len(self.install.maestro.pending(self.watch))
        processed = total - pending
        percent = int((processed) / float(total) * 100.0)
        return total, processed, percent

    def bar(self, prefix, percent):
        percent_count = percent / 10
        progress_bar = ('#' * percent_count) + (' ' * (10 - percent_count))
        return "\r\033[K{0}: [{1}] {2:>2}% ".format(prefix, progress_bar, percent)


class RetrieveAndBuildProgress(Progress):

    def update(self):
        total, processed, percent = self.processed_packages()
        msg = [self.bar("Retrieving", percent)]
        msg.append("({0} requested, {1} retrieved, {2} built)".format(
            total, len(self.install.maestro.retrieved), processed))
        sys.stdout.write(''.join(msg))
        sys.stdout.flush()


class InstallProgress(Progress):

    def update(self):
        total, processed, percent = self.processed_packages()
        msg = [self.bar("Installing", percent)]
        msg.append("({0}/{1})".format(processed, total))
        sys.stdout.write(''.join(msg))
        sys.stdout.flush()
