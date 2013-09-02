from __future__ import unicode_literals, print_function, absolute_import
from datetime import datetime
from StringIO import StringIO

from sh import ErrorReturnCode, pip

from . import util
from gevent.pool import Pool
from gevent.queue import Queue

import io
import os
import hashlib
import urllib2
import urlparse
import tarfile
import gevent


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


class Service(object):
    def __init__(self, callback, concurrency=1, result_queue=None):
        self.callback = callback
        self.result_queue = result_queue
        self.package_queue = Queue()
        self.failed_queue = []

        self.main_greenlet = None
        self.pool = Pool(concurrency)
        self.should_run = True

    def queue(self, package):
        print(' * {0},queueing: {1}'.format(self.__class__.__name__.lower(), package))
        self.package_queue.put(package)

    def consume(self):
        package = self.package_queue.get()
        print(' * {0},consuming: {1}'.format(self.__class__.__name__.lower(), package))
        self.pool.spawn(self._run_service, package)

    def loop(self):
        while self.should_run:
            self.consume()

    def start(self):
        self.main_greenlet = gevent.spawn(self.loop)

    def stop(self, force=False):
        # This will force the current iteraton on `loop()` to be the last one,
        # so the thing we're processing will be able to finish;
        self.should_run = False

        # if the caller is in a hurry, we'll just kill everything mercilessly
        if force and self.main_greenlet:
            self.main_greenlet.kill()

    def _run_service(self, package):
        try:
            self.callback(package)
        except BaseException as exc:
            self.failed_queue.append((package, exc))
            print('failed to run {0} for package {1}: {2}'.format(
                self.__class__.__name__, package, exc))
        else:
            # If the callback worked, let's go ahead and tell the world. If and
            # only if requested by the caller, of course.
            if self.result_queue:
                self.result_queue.put(package)
