from __future__ import unicode_literals, print_function, absolute_import
from collections import namedtuple
from pip.commands.uninstall import UninstallCommand

from gevent.queue import Queue
from gevent.pool import Pool

from .download import PipSource, CurdlingSource, DownloadManager
from .wheelhouse import Curdling
from .installer import Installer
from .index import PackageNotFound
from .uploader import Uploader

import pkg_resources
import gevent
import os


class Env(object):
    def __init__(self, conf=None):
        self.conf = conf or {}
        self.index = self.conf.get('index')
        self.services = {}

    def start_services(self):
        # General params for all the services
        params = {
            'env': self,
            'index': self.index,
            'concurrency': self.conf.get('concurrency'),
        }

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
        self.services['download'] = DownloadManager(sources=sources, **params)
        self.services['curdling'] = Curdling(**params)
        self.services['install'] = Installer(**params)
        self.services['upload'] = Uploader(sources=curdling_urls, **params)

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
