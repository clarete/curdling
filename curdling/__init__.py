from __future__ import unicode_literals, print_function, absolute_import
from collections import namedtuple
from datetime import datetime
from gevent.pool import Pool
from pip.commands.uninstall import UninstallCommand
from sh import ErrorReturnCode, pip
from StringIO import StringIO
from . import util

import io
import os
import hashlib
import urllib2
import urlparse
import tarfile
import pkg_resources


def hash_files(file_list):
    """Hashes the contents of a list of files
    """
    return hashlib.new(
        'sha1',
        ''.join(io.open(f).read() for f in file_list),
    ).hexdigest()


def pip_error(msg):
    # Pip shows the full path for the log file. It will make it
    # harder to test things
    return CurdException(msg
        .replace(os.path.expanduser('~'), '${HOME}')
        .strip())


class CurdException(Exception):
    pass


class CurdManager(object):
    def __init__(self, path, settings=None):
        self.path = path
        self.settings = (settings or {})

        # Saves the mapping of uids to files
        self.mapping = {}

    def curd_path(self, uid):
        path = os.path.join(self.path, uid)
        os.path.isdir(path) or os.makedirs(path)
        return path

    def add(self, requirements):
        uid = hash_files(requirements)
        self.mapping[uid] = requirements
        return uid

    def get(self, uid):
        return (os.path.exists(os.path.join(self.path, uid))
                and Curd(self.path, uid)
                or None)

    def new(self, uid):
        # Trying to use the cache
        curd = self.get(uid)
        if curd:
            return curd

        # No cached curd, let's move on and build our own
        params = {}
        params['wheel_dir'] = self.curd_path(uid)
        params['quiet'] = True
        # params['upgrade'] = True

        if 'index-url' in self.settings:
            params.update({'index_url': self.settings['index-url']})

        if 'extra-index-url' in self.settings:
            params.update({'extra_index_url': self.settings['extra-index-url']})

        # Iterating over all the requirement files we have here
        for reqfile in self.mapping[uid]:
            params.update({'r': reqfile})
            try:
                cmd = pip.wheel(**params)

                # A *nasty* hack to workaround the problem described https:
                # here://github.com/pypa/pip/pull/1162
                if 'due to a pre-existing build directory' in cmd.stdout:
                    raise pip_error(exc.stdout + exc.stderr)

            except ErrorReturnCode as exc:
                raise pip_error(exc.stdout + exc.stderr)

        return self.get(uid)

    def install(self, uid):
        params = {
            'use_wheel': True,
            'no_index': True,
            'find_links': self.curd_path(uid),
            'quiet': True,
        }

        for reqfile in self.mapping[uid]:
            params.update({'r': reqfile})
            try:
                pip.install(**params)
            except ErrorReturnCode as exc:
                raise pip_error(exc.stdout)

    def available(self):
        return (os.path.isdir(self.path)
                and [Curd(self.path, cid) for cid in os.listdir(self.path)]
                or [])

    def retrieve(self, uid):
        # Retrieving the tar file
        url = urlparse.urljoin(self.settings['cache-url'], uid)
        response = urllib2.urlopen(url)
        tarcontent = response.read()

        # Opening the tar StringIO'ed content. Bad things might happen here if
        # the data does not represent a valid tar file
        tar = tarfile.open(
            name='{}.tar'.format(uid),
            mode='r',
            fileobj=StringIO(tarcontent),
        )

        # Extracting each file to our target directory
        for entry in tar:
            tar.extract(entry, path=self.curd_path(uid))

        tar.close()
        return self.get(uid)


class Curd(object):
    def __init__(self, path, uid):
        self.path = os.path.join(path, uid)
        self.uid = uid

    @property
    def created(self):
        return datetime.fromtimestamp(
            os.stat(self.path).st_ctime)

    def __eq__(self, other):
        return self.path == other.path

    def members(self):
        return os.listdir(self.path)


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
    def __init__(self, local_cache_backend):
        self.local_cache = LocalCache(backend=local_cache_backend)

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
            self.install_queue.put(requirement)
            return False

        self.download_queue.put(requirement)
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


class Service(object):
    def __init__(self, callback, result_queue):
        self.callback = callback
        self.result_queue = result_queue
        self.package_queue = []
        self.failed_queue = []
        self.pool = None

    def queue(self, package):
        self.package_queue.append(package)

    def start(self, concurrent=1):
        self.pool = Pool(concurrent)
        for queued in self.package_queue:
            self.package_queue.remove(queued)
            self.pool.spawn(self._run_service, queued)

    def _run_service(self, package):
        try:
            self.callback(package)
        except BaseException as exc:
            self.failed_queue.append((package, exc))
        else:
            # If the callback worked, let's go ahead and tell the world. If and
            # only if requested by the caller, of course.
            if self.result_queue:
                self.result_queue.put(package)
