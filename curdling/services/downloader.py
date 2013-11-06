from __future__ import absolute_import, print_function, unicode_literals
from ..exceptions import RequirementNotFound, UnknownURL, TooManyRedirects, ReportableError
from .. import util
from .base import Service
from distlib import database, metadata, compat, locators

import os
import re
import json
import urllib3
import tempfile
import distlib.version


# Hardcoded vaue for the size of the http pool used a couple times in this
# module. Not the perfect place, though might fix the ClosedPoolError we're
# getting eventually.
POOL_MAX_SIZE = 10

# Number of max redirect follows. See `http_retrieve()` for details.
REDIRECT_LIMIT = 20


def get_locator(conf):
    curds = [CurdlingLocator(u) for u in conf.get('curdling_urls', [])]
    pypi = [PyPiLocator(u) for u in conf.get('pypi_urls', [])]
    return AggregatingLocator(*(curds + pypi), scheme='legacy')


def find_packages(locator, requirement, versions):
    scheme = distlib.version.get_scheme(locator.scheme)
    matcher = scheme.matcher(requirement.requirement)

    result = {}
    if versions:
        slist = []
        for v in versions:
            if matcher.match(matcher.version_class(v)):
                slist.append(v)
        slist = sorted(slist, key=scheme.key)
        if len(slist):
            result = versions[slist[-1]]

    return result


def update_url_credentials(base_url, other_url):
    base = compat.urlparse(base_url)
    other = compat.urlparse(other_url)

    # If they're not from the same server, we return right away without
    # trying to update anything
    if base.hostname != other.hostname or base.port != other.port:
        return other.geturl()

    # Update the `netloc` field and return the `other` url
    return other._replace(netloc=base.netloc).geturl()


def parse_url_and_revision(url):
    parsed_url = compat.urlparse(url)
    revision = None
    if '@' in parsed_url.path:
        path, revision = parsed_url.path.rsplit('@', 1)
        parsed_url = parsed_url._replace(path=path)
    return parsed_url.geturl(), revision


def http_retrieve(pool, url, attempt=0):
    if attempt >= REDIRECT_LIMIT:
        raise TooManyRedirects('Too many redirects')

    # Params to be passed to request. The `preload_content` must be set to
    # False, otherwise `read()` wont honor `decode_content`.
    params = {
        'headers': util.get_auth_info_from_url(url),
        'preload_content': False,
        'redirect': False,
    }

    # Request the url and ensure we've reached the final location
    response = pool.request('GET', url, **params)
    if 'location' in response.headers:
        location = response.headers['location']
        if location.startswith('/'):
            url = compat.urljoin(url, location)
        else:
            url = location
        return http_retrieve(pool, url, attempt=attempt + 1)
    return response, url


def get_opener():
    http_proxy = os.getenv('http_proxy')
    if http_proxy:
        parsed_url = compat.urlparse(http_proxy)
        proxy_headers = util.get_auth_info_from_url(
            http_proxy, proxy=True)
        return urllib3.ProxyManager(
            proxy_url=parsed_url.geturl(),
            proxy_headers=proxy_headers)
    return urllib3.PoolManager()


class ComparableLocator(object):
    def __eq__(self, other):
        return self.base_url == other.base_url

    def __repr__(self):
        return '{0}(\'{1}\')'.format(self.__class__.__name__, self.base_url)


class AggregatingLocator(locators.AggregatingLocator):

    def locate(self, requirement, prereleases=True):
        pkg = util.parse_requirement(requirement)
        for locator in self.locators:
            versions = locator.get_project(pkg.name)
            packages = find_packages(locator, pkg, versions)
            if packages:
                return packages


class PyPiLocator(locators.SimpleScrapingLocator, ComparableLocator):
    def __init__(self, url, **kwargs):
        super(PyPiLocator, self).__init__(url, **kwargs)
        self.opener = get_opener()

    def _get_project(self, name):
        # It sounds lame, but we're trying to match requirements with more than
        # one word separated with either `_` or `-`. Notice that we prefer
        # hyphens cause there is currently way more packages using hyphens than
        # underscores in pypi.p.o. Let's wait for the best here.
        options = [name]
        if '-' in name or '_' in name:
            options = (name.replace('_', '-'), name.replace('-', '_'))

        # Iterate over all the possible names a package can have.
        for package_name in options:
            url = compat.urljoin(self.base_url, '{0}/'.format(
                compat.quote(package_name)))
            found = self._fetch(url, package_name)
            if found:
                return found

    def _visit_link(self, project_name, link):
        self._seen.add(link)
        locators.logger.debug('_fetch() found link: %s', link)
        info = not self._is_platform_dependent(link) \
            and self.convert_url_to_download_info(link, project_name) \
            or None

        versions = {}
        if info:
            self._update_version_data(versions, info)
            return list(versions.items())[0]
        return None, None

    def _fetch(self, url, project_name, subvisit=False):
        locators.logger.debug('fetch(%s, %s)', url, project_name)
        versions = {}
        page = self.get_page(url)
        for link, rel in (page and page.links or []):
            # Let's instrospect one level down
            if self._should_queue(link, url, rel) and not subvisit:
                versions.update(self._fetch(link, project_name, subvisit=True))

            # Let's not see anything twice, I saw this check on distlib it
            # might be useful.
            if link not in self._seen:
                # Well, here we're ensuring that the first link of a given
                # version will be the one. Even if we find another package for
                # the same version, the first one will be used.
                version, distribution = self._visit_link(project_name, link)
                if version and version not in versions:
                    versions[version] = distribution
        return versions

    def get_page(self, url):
        # http://peak.telecommunity.com/DevCenter/EasyInstall#package-index-api
        scheme, netloc, path, _, _, _ = compat.urlparse(url)
        if scheme == 'file' and os.path.isdir(url2pathname(path)):
            url = compat.urljoin(ensure_slash(url), 'index.html')

        # The `retrieve()` method follows any eventual redirects, so the
        # initial url might be different from the final one
        try:
            response, final_url = http_retrieve(self.opener, url)
        except urllib3.exceptions.MaxRetryError:
            return

        content_type = response.headers.get('content-type', '')
        if locators.HTML_CONTENT_TYPE.match(content_type):
            data = response.data
            encoding = response.headers.get('content-encoding')
            if encoding:
                decoder = self.decoders[encoding]   # fail if not found
                data = decoder(data)
            encoding = 'utf-8'
            m = locators.CHARSET.search(content_type)
            if m:
                encoding = m.group(1)
            try:
                data = data.decode(encoding)
            except UnicodeError:
                data = data.decode('latin-1')    # fallback
            return locators.Page(data, final_url)


class CurdlingLocator(locators.Locator, ComparableLocator):

    def __init__(self, url, **kwargs):
        super(CurdlingLocator, self).__init__(**kwargs)
        self.base_url = url
        self.url = url
        self.opener = get_opener()
        self.requirements_not_found = []

    def get_distribution_names(self):
        return json.loads(
            http_retrieve(self.opener,
                compat.urljoin(self.url, 'api'))[0].data)

    def _get_project(self, name):
        # Retrieve the info
        url = compat.urljoin(self.url, 'api/' + name)
        try:
            response, _ = http_retrieve(self.opener, url)
        except urllib3.exceptions.MaxRetryError:
            return None

        if response.status == 200:
            data = json.loads(response.data)
            return dict((v['version'], self._get_distribution(v)) for v in data)
        else:
            self.requirements_not_found.append(name)

    def _get_distribution(self, version):
        # Source url for the package
        source_url = version['urls'][0]  # TODO: prefer whl files

        # Build the metadata
        mdata = metadata.Metadata(scheme=self.scheme)
        mdata.name = version['name']
        mdata.version = version['version']
        mdata.download_url = source_url['url']

        # Building the dist and associating the download url
        distribution = database.Distribution(mdata)
        distribution.locator = self
        return distribution


class Finder(Service):

    def __init__(self, *args, **kwargs):
        super(Finder, self).__init__(*args, **kwargs)
        self.opener = get_opener()
        self.locator = get_locator(self.conf)

    def handle(self, requester, data):
        requirement = data['requirement']
        prereleases = self.conf.get('prereleases', True)
        distribution = self.locator.locate(requirement, prereleases)
        if not distribution:
            raise RequirementNotFound(
                'Requirement `{0}\' not found'.format(requirement))
        return {
            'requirement': data['requirement'],
            'url': distribution.metadata.download_url,
            'locator_url': distribution.locator.base_url,
        }

    def get_servers_to_update(self):
        failures = {}
        for locator in self.locator.locators:
            if isinstance(locator, CurdlingLocator) and locator.requirements_not_found:
                failures[locator.base_url] = locator.requirements_not_found
        return failures


class Downloader(Service):

    def __init__(self, *args, **kwargs):
        super(Downloader, self).__init__(*args, **kwargs)
        self.opener = get_opener()
        self.locator = get_locator(self.conf)

        # List of packages that we're aware of, so people that want to send
        # jobs to the downloader can avoid duplications.
        self.processing_packages = set()

    def queue(self, requester, **data):
        self.processing_packages.add(os.path.basename(data['url']))
        super(Downloader, self).queue(requester, **data)

    def handle(self, requester, data):
        field_name, location = self.download(data['url'], data.get('locator_url'))
        return {
            'requirement': data['requirement'],
            field_name: location,
        }

    def download(self, url, locator_url=None):
        final_url = url

        # We're dealing with a requirement, not a link
        if locator_url:
            # The locator's URL might contain authentication credentials, while
            # the package URL might not (the scraper doesn't return with that
            # information)
            final_url = update_url_credentials(locator_url, url)

        # Find out the right handler for the given protocol present in the
        # download url.
        protocol_mapping = {
            re.compile('^https?'): self._download_http,
            re.compile('^git\+'): self._download_git,
            re.compile('^hg\+'): self._download_hg,
            re.compile('^svn\+'): self._download_svn,
        }

        try:
            handler = [i for i in protocol_mapping.keys() if i.findall(url)][0]
        except IndexError:
            raise UnknownURL(
                util.spaces(3, '\n'.join([
                    '"{0}"'.format(url),
                    '',
                    'Your URL looks wrong. Make sure it\'s a valid HTTP',
                    'link or a valid VCS link prefixed with the name of',
                    'the VCS of your choice. Eg.:',
                    '',
                    ' $ curd install https://pypi.python.org/simple/curdling/curdling-0.1.2.tar.gz\n'
                    ' $ curd install git+ssh://github.com/clarete/curdling.git\n'
                ])))

        # Remove the protocol prefix from the url before passing to
        # the handler which is not prepared to handle urls starting
        # with `vcs+`. This RE is smart enough to handle plus (+)
        # signs out of the scheme. Like in this example:
        #   https://launchpad.com/path/+download/dirspec-13.10.tar.gz
        url = re.sub('^([^\+]+)\+([^:]+\:)', r'\2', final_url)
        return protocol_mapping[handler](url)

    def _download_http(self, url):
        response, final_url = http_retrieve(self.opener, url)
        if final_url:
            url = final_url
        if response.status != 200:
            raise ReportableError(
                'Failed to download url `{0}\': {1} ({2})'.format(
                    url,
                    response.status,
                    compat.httplib.responses[response.status],
                ))

        # Define what kind of package we've got
        field_name = 'wheel' if url.endswith('.whl') else 'tarball'

        # Now that we're sure that our request was successful
        header = response.headers.get('content-disposition', '')
        file_name = re.findall(r'filename=\"?([^;\"]+)', header)
        return field_name, self.index.from_data(
            file_name and file_name[0] or url,
            response.read(cache_content=True, decode_content=False))

    def _download_git(self, url):
        destination = tempfile.mkdtemp()
        url, revision = parse_url_and_revision(url)
        util.execute_command('git', 'clone', url, destination)
        if revision:
            util.execute_command('git', 'reset', '--hard', revision,
                cwd=destination)
        return 'directory', destination

    def _download_hg(self, url):
        destination = tempfile.mkdtemp()
        url, revision = parse_url_and_revision(url)
        util.execute_command('hg', 'clone', url, destination)
        if revision:
            util.execute_command('hg', 'update', '-q', revision,
                cwd=destination)
        return 'directory', destination

    def _download_svn(self, url):
        destination = tempfile.mkdtemp()
        url, revision = parse_url_and_revision(url)
        params = ['svn', 'co', '-q']
        if revision:
            params.append('-r')
            params.append(revision)
        params += [url, destination]
        util.execute_command(*params)
        return 'directory', destination
