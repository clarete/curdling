from __future__ import absolute_import, unicode_literals, print_function
from pip.req import InstallRequirement
from pip.index import PackageFinder

import re
import os
import urllib2
import urlparse

from . import util, ReportableError
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
        response = urllib2.urlopen(url)
        header = response.info().get('content-disposition', '')
        file_name = re.findall(r'filename=([^;]+)', header)
        return self.index.from_data(
            file_name and file_name[0] or url,
            response.read())

    def attempt(self, package, source):
        self.logger.level(2, ' * downloadmanager: ', end='')
        try:
            url = source.url(package)
            return self.download(package, url)
        except Exception as exc:
            # Showing the source name
            self.logger.level(2, 'from %s ',
                source.__class__.__name__.lower(), end='')

            # Showing the cause
            args = getattr(exc, 'args')
            msg = args and str(args[0]) or exc.msg
            self.logger.level(2, '... failed (%s)', msg)
            self.logger.traceback(4, '', exc=exc)
        else:
            self.logger.level(2, '... ok')

    def retrieve(self, package):
        for source in self.sources:
            path = self.attempt(package, source)

            # We log all the attempts to the second level. But if we can make
            # it, that's where we get out of the loop, avoiding the need to
            # keep iterating over other sources.
            if path:
                return path
        raise ReportableError('No distributions found for {0}'.format(package))
