from __future__ import absolute_import, unicode_literals, print_function
from collections import defaultdict
from pip.req import InstallRequirement
from pip.index import PackageFinder

import io
import os
import errno
import shutil
import urllib2

from gevent.pool import Pool

from .util import gen_package_path


class MemoryStorage(defaultdict):
    def __init__(self):
        super(MemoryStorage, self).__init__(list)

    def write(self, path, data):
        self[path].append(data)
        return path

    def read(self, path):
        return (b'').join(self[path])


class DirectoryStorage(dict):
    def __init__(self, path):
        super(DirectoryStorage, self).__init__()
        self.path = path

    def build_path(self, path):
        full = os.path.join(self.path, path)
        try:
            os.makedirs(os.path.dirname(full))
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise exc
        return full

    def __getitem__(self, item):
        return io.open(self.build_path(item)).read()

    def __setitem__(self, item, value):
        with io.open(self.build_path(item), 'wb') as f:
            f.write(value)

    def __delitem__(self, item):
        os.unlink(os.path.join(self.path, item))

    def __del__(self):
        shutil.rmtree(self.path)

    def write(self, path, data):
        self[path] = data
        return path

    def read(self, path):
        return self[path]


class PipSource(object):
    def __init__(self, dirs=None, urls=None):
        self.finder = PackageFinder(
            find_links=dirs or [],
            index_urls=urls or [])

    def url(self, package):
        return self.finder.find_requirement(
            InstallRequirement.from_line(package),
            True).url


class DownloadManager(object):
    def __init__(self, sources=None, storage=None, result_queue=None):
        self.sources = sources
        self.storage = storage
        self.result_queue = result_queue
        self.package_queue = []
        self.pool = None

    def queue(self, package):
        self.package_queue.append(package)

    def start(self, concurrent=1):
        self.pool = Pool(concurrent)
        for queued in self.package_queue:
            self.package_queue.remove(queued)
            self.pool.spawn(self.retrieve, queued)
        self.pool.join()
        self.pool.kill()

    def download(self, package_name, url):
        pkg = urllib2.urlopen(url).read()
        path = os.path.join(
            gen_package_path(package_name),
            os.path.basename(url))
        return self.storage.write(path, pkg)

    def retrieve(self, package):
        for source in self.sources:
            url = source.url(package)
            path = self.download(package, url)

            if self.result_queue:
                self.result_queue.put(path)
            return path
        return False
