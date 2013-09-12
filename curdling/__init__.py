from __future__ import unicode_literals, print_function, absolute_import
from collections import namedtuple
from distlib.database import DistributionPath
from distlib.util import parse_requirement
from pip.commands.uninstall import UninstallCommand

from gevent.queue import JoinableQueue
from gevent.pool import Pool

from .logging import Logger, ReportableError
from .download import DownloadManager
from .wheelhouse import Curdling
from .installer import Installer
from .index import PackageNotFound
from .uploader import Uploader

import gevent
import os


PACKAGE_BLACKLIST = (
    'setuptools',
)


class Env(object):
    def __init__(self, conf):
        self.conf = conf
        self.index = self.conf.get('index')
        self.logger = Logger('main', conf.get('log_level'))
        self.services = {}

    def start_services(self):
        # General params for all the services
        args = self.conf
        args.update({
            'env': self,
            'index': self.index,
            'conf': self.conf,
        })

        # Tiem to create our tasty services :)
        self.services['download'] = DownloadManager(**args)
        self.services['curdling'] = Curdling(**args)
        self.services['install'] = Installer(**args)
        self.services['upload'] = Uploader(sources=args.get('curdling_urls', []), **args)

        # Creating a kind of a pipe that looks like this:
        # "download > curdling > install"
        self.services['curdling'].subscribe(self.services['download'])
        self.services['install'].subscribe(self.services['download'])
        self.services['install'].subscribe(self.services['curdling'])

        # If the user wants to share local wheels, let's do it! :)
        if args.get('upload'):
            self.services['upload'].subscribe(self.services['curdling'])
            self.services['upload'].subscribe(self.services['install'])

        # Starting the services
        [x.start() for x in self.services.values()]

    def wait(self):
        # Loop through all the services checking their package_queue
        while True:
            if sum(x.package_queue.qsize() for x in self.services.values()):
                gevent.sleep(1)
            else:
                break

    def shutdown(self):
        # Let's show some stats
        errors = {}

        # Gathers all the failures across all the servicess
        for name, service in self.services.items():
            if service.failed_queue:
                self.logger.level(3, "Step: %s", name, indent=2)
                errors[name] = 0
            for package, exc in service.failed_queue:
                errors[name] += 1
                failure = '{0}: {1}'.format(package, exc)
                self.logger.level(3, "%s", failure, indent=4)
            service.pool.kill()

        if not errors:
            self.logger.level(3, "We're good to go!")
        return errors

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

        # Well, the package is installed, let's just bail
        if self.check_installed(requirement):
            return True

        # Looking for built packages
        try:
            path = self.index.get("{0};whl".format(requirement))
            data.update({'path': path})
            self.services['install'].queue(requirement, requester, **data)
            return False
        except PackageNotFound:
            pass

        # Looking for downloaded packages. If there's packages of any of the
        # following distributions, we'll just build the wheel
        try:
            path = self.index.get("{0};~whl".format(requirement))
            data.update({'path': path})
            self.services['curdling'].queue(requirement, requester, **data)
            return False
        except PackageNotFound:
            pass

        # Nops, we really don't have the package
        self.services['download'].queue(requirement, requester, **data)
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
