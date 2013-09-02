from __future__ import unicode_literals, print_function, absolute_import
from collections import namedtuple
from pip.commands.uninstall import UninstallCommand

from gevent.queue import Queue
from gevent.pool import Pool

from . import util
from .download import PipSource, DownloadManager
from .wheelhouse import Curdling
from .installer import Installer

import pkg_resources
import gevent
import os


class LocalCache(object):
    def __init__(self, backend):
        self.backend = backend

    def put(self, name, val):
        self.backend[name] = val

    def get(self, name):
        return self.backend.get(name)

    def scan_dir(self, path):
        allowed = ('.whl',)

        for root, dirs, files in os.walk(path):
            for name in files:
                n, ext = os.path.splitext(name)
                if ext in allowed:
                    pkg_name, version, impl, abi, plat = n.split('-')
                    self.put(
                        '{0}=={1}'.format(pkg_name, version),
                        os.path.join(util.gen_package_path(pkg_name), name))


class Env(object):
    def __init__(self, conf=None):
        self.conf = conf or {}
        self.services = {}
        self.local_cache = LocalCache(
            backend=self.conf.get('cache_backend', {}))

    def start_services(self):
        # General params for all the services
        params = {
            'storage': self.conf.get('storage'),
            'concurrency': self.conf.get('concurrency'),
        }

        sources = [PipSource(urls=self.conf.get('urls'))]
        self.services['download'] = DownloadManager(sources=sources, **params)
        self.services['curdling'] = Curdling(**params)
        self.services['install'] = Installer(**params)

        # Creating a kind of a pipe that looks like this:
        # "download > curdling > install"
        self.services['download'].result_queue = self.services['curdling'].package_queue
        # self.services['curdling'].result_queue = self.services['install'].package_queue

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
        if self.check_installed(requirement):
            return True

        elif self.local_cache.get(requirement):
            self.services['install'].queue(requirement)
            return False

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
