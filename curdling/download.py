from __future__ import absolute_import, unicode_literals, print_function
from pip.req import InstallRequirement
from pip.index import PackageFinder

import re
import os
import urlparse
import requests

from . import util, ReportableError
from .service import Service


class CurdlingSource(object):
    def __init__(self, url):
        self.base_url = url

    def credentials(self, link):
        return None

    def url(self, package):
        return urlparse.urljoin(self.base_url, package)


class PipSource(object):
    def __init__(self, dirs=None, urls=None):
        self.finder = PackageFinder(
            find_links=dirs or [],
            index_urls=urls or [])

    def credentials(self, link):
        parsed_link = urlparse.urlparse(link)

        for index in self.finder.index_urls:
            parsed_index = urlparse.urlparse(index)
            if parsed_index.hostname == parsed_link.hostname and \
                   parsed_index.port == parsed_link.port:
                return (parsed_index.username, parsed_index.password)

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

    def download(self, source, url):
        response = requests.get(url, auth=source.credentials(url))
        response.raise_for_status()

        # Now that we're sure that our request was successful
        header = response.headers.get('content-disposition', '')
        file_name = re.findall(r'filename=([^;]+)', header)
        return self.index.from_data(
            file_name and file_name[0] or url,
            response.content)

    def attempt(self, package, source):
        self.logger.level(
            2, ' * downloadmanager.attempt(package=%s, source=%s): ',
            package, source.__class__.__name__.lower(), end='')
        try:
            path = self.download(source, source.url(package))
            self.logger.level(2, ' ... ok')
            return path
        except Exception as exc:
            # Showing the source name
            self.logger.level(2, 'from %s ',
                source.__class__.__name__.lower(), end='')

            # Showing the cause
            args = getattr(exc, 'args')
            msg = args and str(args[0]) or exc.msg
            self.logger.level(2, '... failed (%s)', msg)
            self.logger.traceback(4, '', exc=exc)

    def retrieve(self, package, sender_data):
        for source in self.sources:
            path = self.attempt(package, source)

            # We log all the attempts to the second level. But if we can make
            # it, that's where we get out of the loop, avoiding the need to
            # keep iterating over other sources.
            if path:
                return {"path": path}
        raise ReportableError('No distributions found for {0}'.format(package))
