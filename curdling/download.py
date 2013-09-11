from __future__ import absolute_import, unicode_literals, print_function
from urllib2 import HTTPPasswordMgrWithDefaultRealm
from distlib.compat import (
    urlparse, build_opener, HTTPBasicAuthHandler, Request,
)
from distlib.locators import (
    Locator, AggregatingLocator, SimpleScrapingLocator, JSONLocator,
)

import re

from . import util, ReportableError
from .service import Service


def get_locator(conf):
    return AggregatingLocator(*([
        CurdlingLocator(u) for u in conf.get('curdling_urls', [])
    ] + [
        SimpleLocator(u, timeout=3.0) for u in conf.get('pypi_urls', [])
    ]), scheme='adaptive')


def get_opener(url):
    # Set the actual base_url, without credentials info
    url = urlparse(url)
    base_url = lambda p=url.path: '{0}://{1}:{2}{3}'.format(
        url.scheme, url.hostname, url.port or 80, p)

    # Prepare the list of handlers that will be added to the opener
    handlers = []
    if url.username and url.password:
        manager = HTTPPasswordMgrWithDefaultRealm()
        manager.add_password(None, base_url(), url.username, url.password)
        manager.add_password(None, base_url('/packages/'), url.username, url.password)
        handlers.append(HTTPBasicAuthHandler(manager))

    # Define a new opener based on the things we found above
    return base_url(), build_opener(*handlers)


class CurdlingLocator(Locator):
    def __init__(self, url, **kwargs):
        super(CurdlingLocator, self).__init__(**kwargs)
        self.url =  url

    def get_distribution_names(self):
        return

    def _get_project(self, name):
        return


class SimpleLocator(SimpleScrapingLocator):
    def __init__(self, *args, **kwargs):
        super(SimpleLocator, self).__init__(*args, **kwargs)
        self.base_url, self.opener = get_opener(self.base_url)


class DownloadManager(Service):

    def download(self, opener, url):
        response = opener.open(Request(url))
        try:
            content = []
            headers = response.info()
            blocksize = 8192
            read = 0
            while True:
                block = response.read(blocksize)
                if not block:
                    break
                read += len(block)
                content.append(block)
        finally:
            response.close()

        # Now that we're sure that our request was successful
        header = response.headers.get('content-disposition', '')
        file_name = re.findall(r'filename=([^;]+)', header)
        return self.index.from_data(
            file_name and file_name[0] or url,
            b''.join(content))

    def attempt(self, package):
        self.logger.level(
            2, ' * downloadmanager.attempt(package=%s): ',
            package, end='')
        try:
            locator = get_locator(self.conf)
            requirement = locator.locate(package)
            if requirement is None:
                raise RuntimeError(
                    'No distribution found for {0}'.format(package))

            # Here we're passing the same opener to the download function. In
            # other words, we just want to use the same locator that was used
            # to find the package to download it.
            path = self.download(
                requirement.locator.opener,
                requirement.download_url)

            self.logger.level(2, ' ... ok')
            return path
        except Exception as exc:
            # Showing the cause
            args = getattr(exc, 'args')
            msg = args and str(args[0]) or exc.msg
            self.logger.level(2, '... failed (%s)', msg)
            self.logger.traceback(4, '', exc=exc)

    def handle(self, package, sender_data):
        path = self.attempt(package)

        # We log all the attempts to the second level. But if we can make it,
        # that's where we get out of the loop, avoiding the need to keep
        # iterating over other sources.
        if path:
            return {"path": path}
        raise ReportableError('No distributions found for {0}'.format(package))
