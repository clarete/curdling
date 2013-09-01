from __future__ import absolute_import, unicode_literals, print_function
from collections import defaultdict
from pip.req import InstallRequirement
from pip.index import PackageFinder

import os
import urllib2

from .util import gen_package_path


class MemoryStorage(defaultdict):
    def __init__(self):
        super(MemoryStorage, self).__init__(list)

    def write(self, path, data):
        self[path].append(data)
        return path

    def read(self, path):
        return ''.join(self[path])


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
