from __future__ import absolute_import, unicode_literals, print_function
from collections import defaultdict
from pip.req import InstallRequirement
from pip.index import PackageFinder
from pip.exceptions import DistributionNotFound

import io
import os
import errno
import shutil
import urllib2
import pkg_resources

from gevent.pool import Pool

from . import util, Service


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
        ext = util.split_name(os.path.basename(url))[1]
        data = urllib2.urlopen(url).read()
        return self.index.from_data(package_name, ext, data)

    def retrieve(self, package):
        for source in self.sources:
            url = source.url(package)
            return self.download(package, url)
        raise DistributionNotFound
