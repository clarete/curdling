from __future__ import absolute_import, unicode_literals, print_function
from urllib2 import HTTPPasswordMgrWithDefaultRealm, HTTPError
from urlparse import urljoin
from distlib import database, metadata, compat, locators

from . import util, ReportableError
from .service import Service
from .signal import Signal

import re
import json


def get_locator(conf):
    return locators.AggregatingLocator(*([
        CurdlingLocator(u) for u in conf.get('curdling_urls', [])
    ] + [
        SimpleLocator(u, timeout=3.0) for u in conf.get('pypi_urls', [])
    ]), scheme='legacy')


def get_opener(url):
    # Set the actual base_url, without credentials info
    url = compat.urlparse(url)
    base_url = lambda p=url.path: '{0}://{1}:{2}{3}'.format(
        url.scheme, url.hostname, url.port or 80, p)

    # Prepare the list of handlers that will be added to the opener
    handlers = []
    if url.username and url.password:
        manager = HTTPPasswordMgrWithDefaultRealm()
        manager.add_password(None, base_url(), url.username, url.password)
        manager.add_password(None, base_url('/packages/'), url.username, url.password)
        handlers.append(compat.HTTPBasicAuthHandler(manager))

    # Define a new opener based on the things we found above
    return base_url(), compat.build_opener(*handlers)


class CurdlingLocator(locators.Locator):

    def __init__(self, url, **kwargs):
        super(CurdlingLocator, self).__init__(**kwargs)
        self.original_url = url
        self.url, self.opener = get_opener(url)
        self.packages_not_found = []

    def get_distribution_names(self):
        url = urljoin(self.url, 'api')
        response = self.opener.open(compat.Request(url))
        return json.loads(response.read())

    def _get_project(self, name):
        # Retrieve the info
        url = urljoin(self.url, 'api/' + name)
        try:
            response = self.opener.open(compat.Request(url))
        except HTTPError as exc:
            # We just bail if any 404 HTTP Errors happened. Cause it just means
            # that the package was not found.
            if exc.getcode() == 404:
                self.packages_not_found.append(name)
                return

            # If anything else happens, we let it blow up, so the user can se
            # how to fix the issue.
            raise exc

        data = json.loads(response.read())
        result = {}

        for version in data:
            # Source url for the package
            source_url = version['urls'][0]  # TODO: prefer whl files

            # Build the metadata
            mdata = metadata.Metadata(scheme=self.scheme)
            mdata.name = version['name']
            mdata.version = version['version']
            mdata.source_url = mdata.download_url = source_url['url']

            # Building the dist and associating the download url
            distribution = database.Distribution(mdata)
            distribution.locator = self
            result[version['version']] = distribution

        return result


class SimpleLocator(locators.SimpleScrapingLocator):
    def __init__(self, *args, **kwargs):
        super(SimpleLocator, self).__init__(*args, **kwargs)
        self.base_url, self.opener = get_opener(self.base_url)


class Downloader(Service):

    def __init__(self, *args, **kwargs):
        super(Downloader, self).__init__(*args, **kwargs)
        self.locator = get_locator(self.conf)

    def handle(self, requester, package, sender_data):
        path = self.attempt(package)

        # We log all the attempts to the second level. But if we can make it,
        # that's where we get out of the loop, avoiding the need to keep
        # iterating over other sources.
        if path:
            return {"path": path}
        raise RuntimeError('Package `{0}\' not found'.format(package))

    def get_servers_to_update(self):
        failures = {}
        for locator in self.locator.locators:
            if isinstance(locator, CurdlingLocator) and locator.packages_not_found:
                failures[locator.original_url] = locator.packages_not_found
        return failures

    # -- Private API of the Download service --

    def download(self, opener, url):
        response = opener.open(compat.Request(url))
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
        try:
            prereleases = self.conf.get('prereleases', True)
            requirement = self.locator.locate(package, prereleases)
            if requirement is None:
                raise RuntimeError('Package `{0}\' not found'.format(package))

            # Here we're passing the same opener to the download function. In
            # other words, we just want to use the same locator that was used
            # to find the package to download it.
            path = self.download(
                requirement.locator.opener,
                requirement.download_url)
            return path
        except Exception as exc:
            # Showing the cause
            args = getattr(exc, 'args')
            msg = args and str(args[0]) or exc.msg
            # self.logger.level(2, '   * %s ... failed (%s)', self.name, msg)
            self.logger.traceback(4, '', exc=exc)
