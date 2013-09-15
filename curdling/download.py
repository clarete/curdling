from __future__ import absolute_import, unicode_literals, print_function
from urllib2 import HTTPPasswordMgrWithDefaultRealm, HTTPError, URLError
from urlparse import urljoin
from distlib import database, metadata, compat, locators

from . import util, ReportableError
from .service import Service
from .signal import Signal

import re
import json

def get_locator(logger, conf):
    return locators.AggregatingLocator(*([
        CurdlingLocator(logger, u) for u in conf.get('curdling_urls', [])
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

    def __init__(self, logger, url, **kwargs):
        super(CurdlingLocator, self).__init__(**kwargs)
        self.original_url = url
        self.logger = logger
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
        except (URLError, HTTPError) as exc:
            # We just bail if any 404 HTTP Errors happened. Cause it just means
            # that the package was not found.
            if getattr(exc, 'getcode', lambda: -1)() == 404:
                self.packages_not_found.append(name)

            # We can't raise an exception here, but we can still log the
            # exception so the user will know what's going on
            self.logger.traceback(4, 'Error reaching curd server', exc=exc)
            return

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

    def _get_project(self, name):
        # Cleaning up our caches
        self._seen.clear()
        self._page_cache.clear()
        url = urljoin(self.base_url, '%s/' % compat.quote(name))
        return self.fetch(url, name)

    def visit_link(self, project_name, link, versions):
        self._seen.add(link)
        locators.logger.debug('_fetch() found link: %s', link)
        info = not self._is_platform_dependent(link) \
            and self.convert_url_to_download_info(link, project_name) \
            or None

        if info:
            self._update_version_data(versions, info)

    def fetch(self, url, project_name):
        locators.logger.debug('_fetch(%s, %s)', url, project_name)
        versions = {}
        page = self.get_page(url)
        for link, rel in (page and page.links or []):
            if link not in self._seen:
                self.visit_link(project_name, link, versions)
        return versions


class Downloader(Service):

    def __init__(self, *args, **kwargs):
        super(Downloader, self).__init__(*args, **kwargs)
        self.locator = get_locator(self.logger, self.conf)

    def handle(self, requester, package, sender_data):
        prereleases = self.conf.get('prereleases', True)
        requirement = self.locator.locate(package, prereleases)
        if requirement is None:
            raise ReportableError('Package `{0}\' not found'.format(package))

        # Here we're passing the same opener to the download function. In
        # other words, we just want to use the same locator that was used
        # to find the package to download it.
        return {"path": self.download(
            requirement.locator.opener,
            requirement.download_url)}

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
