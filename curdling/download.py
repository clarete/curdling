from __future__ import absolute_import, unicode_literals, print_function
from pip.req import InstallRequirement
from pip.index import PackageFinder
from pip.exceptions import DistributionNotFound

import re
import os
import urllib2
import urlparse

from . import util
from .service import Service


class CurdlingSource(object):
    def __init__(self, url):
        self.base_url = url

    def url(self, package):
        return urlparse.urljoin(self.base_url, package)


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
        print(' * downloadmanager:url {0}'.format(url), end='')
        try:
            response = urllib2.urlopen(url)
        except (urllib2.URLError, urllib2.HTTPError) as exc:
            print('...failed: {0}'.format(exc))
            raise exc
        print('...ok')

        # Reading the response object to find our stuff
        header = response.info().get('content-disposition', '')
        file_name = re.findall(r'filename=([^;]+)', header)
        file_name = file_name and file_name[0] or url
        data = response.read()
        return self.index.from_data(file_name, data)

    def retrieve(self, package):
        for source in self.sources:
            url = source.url(package)
            return self.download(package, url)
        raise DistributionNotFound
