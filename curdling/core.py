from __future__ import unicode_literals, print_function, absolute_import
from collections import namedtuple
from pip.commands.uninstall import UninstallCommand

from gevent.queue import Queue
from gevent.pool import Pool

from . import util
from .download import PipSource, DownloadManager
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
                if name.startswith('.'):
                    continue

                n, ext = os.path.splitext(name)
                if ext in allowed:
                    pkg_name, version, impl, abi, plat = n.split('-')
                    self.put(
                        '{0}=={1}'.format(pkg_name, version),
                        os.path.join(util.gen_package_path(pkg_name), name))


class Env(object):
    def __init__(self, cache_backend, storage=None):
        self.local_cache = LocalCache(backend=cache_backend)
        self.storage = storage
        self.download_manager = None
        self.install_manager = None

    def start_download_manager(self, source_urls):
        sources = [PipSource(urls=source_urls)]
        self.download_manager = DownloadManager(
            sources=sources, storage=self.storage)
        self.download_manager.start()

    def start_install_manager(self):
        self.install_manager = Installer(storage=self.storage)
        self.install_manager.start()

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
            self.install_manager.queue(requirement)
            return False

        self.download_manager.queue(requirement)
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
