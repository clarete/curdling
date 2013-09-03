from __future__ import absolute_import, unicode_literals, print_function
from pip.req import InstallRequirement
from pip.index import PackageFinder
from pip.exceptions import DistributionNotFound

import os
import urllib2

from . import util
from .service import Service


class PipSource(object):
    def __init__(self, dirs=None, urls=None):
        self.finder = PackageFinder(
            find_links=dirs or [],
            index_urls=urls or [])

    def url(self, package):
        pkg = InstallRequirement.from_line(package)
        return self.finder.find_requirement(pkg, True).url


class DownloadManager(Service):
    def __init__(self, sources, *args, **kwargs):
        self.sources = sources
        self.index = kwargs.pop('index')
        super(DownloadManager, self).__init__(
            callback=self.retrieve,
            *args, **kwargs)

    def download(self, package_name, url):
        print('downloading url {0}'.format(url))
        data = urllib2.urlopen(url).read()
        return self.index.from_data(url, data)

    def retrieve(self, package):
        for source in self.sources:
            url = source.url(package)
            return self.download(package, url)
        raise DistributionNotFound
