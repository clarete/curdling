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

from . import Service
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

    def build_path(self, item):
        full = os.path.join(self.path, gen_package_path(item), item)
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
        os.unlink(self.build_path(item))

    def delete(self):
        shutil.rmtree(self.path)

    def write(self, path, data):
        self[path] = data
        return path

    def find(self, pkg, allowed=('.gz', '.zip', '.whl')):
        subpath = gen_package_path(pkg)
        full = os.path.join(self.path, subpath)
        return [os.path.join(subpath, m)
                for m in os.listdir(full)
                if os.path.splitext(m)[1] in allowed]

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


class DownloadManager(Service):
    def __init__(self, sources=None, storage=None, result_queue=None):
        super(DownloadManager, self).__init__(
            callback=self.retrieve,
            result_queue=result_queue)
        self.sources = sources
        self.storage = storage

    def download(self, package_name, url):
        pkg = urllib2.urlopen(url).read()
        return self.storage.write(os.path.basename(url), pkg)

    def retrieve(self, package):
        for source in self.sources:
            url = source.url(package)
            return self.download(package, url)
        return False
