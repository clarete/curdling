from __future__ import absolute_import, unicode_literals, print_function
from collections import defaultdict
from pip.req import InstallRequirement
from pip.index import PackageFinder

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
    def __init__(self, sources=None, storage=None):
        self.sources = sources
        self.storage = storage

    def download(self, package_name, url):
        pkg = urllib2.urlopen(url).read()
        path = gen_package_path(package_name)
        return self.storage.write(path, pkg)

    def retrieve(self, package):
        for source in self.sources:
            pkg = self.download(package, source.url(package))
            return pkg
        return False
