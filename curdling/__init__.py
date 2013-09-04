from __future__ import unicode_literals, print_function, absolute_import
from collections import namedtuple
from pip.commands.uninstall import UninstallCommand

from gevent.queue import Queue
from gevent.pool import Pool

from .logging import Logger, ReportableError
from .download import PipSource, CurdlingSource, DownloadManager
from .wheelhouse import Curdling
from .installer import Installer
from .index import PackageNotFound
from .uploader import Uploader

import pkg_resources
import gevent
import os


class Env(object):
    def __init__(self, conf):
        self.conf = conf
        self.index = self.conf.get('index')
        self.logger = Logger('main', conf.get('log_level'))
        self.services = {}

    def start_services(self):
        # General params for all the services
        self.conf.update({
            'env': self,
            'index': self.index,
        })

        # Defines the priority of where we're gonna look for packages first. As
        # you can see clearly here, curdling is our prefered repo.
        source_types = (
            ('curdling_urls', CurdlingSource),
            ('pypi_urls', PipSource),
        )

        # Retrieving sources from the args object fed from the user
        sources = []

        curdling_urls = self.conf.get('curdling_urls')
        for url in curdling_urls:
            sources.append(CurdlingSource(url=url))

        pypi_urls = self.conf.get('pypi_urls')
        if pypi_urls:
            sources.append(PipSource(urls=pypi_urls))

        # Tiem to create our tasty services :)
        self.services['download'] = DownloadManager(sources=sources, **self.conf)
        self.services['curdling'] = Curdling(**self.conf)
        self.services['install'] = Installer(**self.conf)
        self.services['upload'] = Uploader(sources=curdling_urls, **self.conf)

        # Creating a kind of a pipe that looks like this:
        # "download > curdling > install"
        self.services['curdling'].subscribe(self.services['download'])
        self.services['install'].subscribe(self.services['curdling'])

        # If the user wants to share local wheels, let's do it! :)
        if self.conf.upload:
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
        try:
            pkg_resources.get_distribution(package)
            return True
        except (pkg_resources.VersionConflict,
                pkg_resources.DistributionNotFound):
            return False

    def request_install(self, requirement):
        # Well, the package is installed, let's just bail
        if self.check_installed(requirement):
            return True

        # Looking for built packages
        try:
            self.index.get("{0};whl".format(requirement))
            self.services['install'].queue(requirement)
            return False
        except PackageNotFound:
            pass

        # Looking for downloaded packages. If there's packages of any of the
        # following distributions, we'll just build the wheel
        try:
            self.index.get("{0};~whl".format(requirement))
            self.services['curdling'].queue(requirement)
            return False
        except PackageNotFound:
            pass

        # Nops, we really don't have the package
        self.services['download'].queue(requirement)
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
