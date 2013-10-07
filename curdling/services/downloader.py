from __future__ import absolute_import, print_function, unicode_literals
from ..exceptions import ReportableError, UnknownProtocol
from .. import util
from .base import Service
from distlib import database, metadata, compat, locators

import re
import json
import urllib3
import tempfile
import distlib.version


# Hardcoded vaue for the size of the http pool used a couple times in this
# module. Not the perfect place, though might fix the ClosedPoolError we're
# getting eventually.
POOL_MAX_SIZE = 10


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

    # Since I can't change the `ParseResult` object returned by `urlparse`,
    # I'll have to do that manually and that stinks.
    scheme, netloc, path, params, query, fragment = list(other)
    return compat.urlunparse(
        (scheme, base.netloc, path, params, query, fragment))


class Pool(urllib3.PoolManager):

    def retrieve(self, url):
        # Params to be passed to request. The `preload_content` must be set to
        # False, otherwise `read()` wont honor `decode_content`.
        params = {
            'headers': util.get_auth_info_from_url(url),
            'preload_content': False,
        }

        # Request the url and ensure we've reached the final location
        response = self.request('GET', url, **params)
        return response, response.get_redirect_location() or url


class AggregatingLocator(locators.AggregatingLocator):

    def locate(self, requirement, prereleases=True):
        pkg = util.parse_requirement(requirement)
        for locator in self.locators:
            versions = locator.get_project(pkg.name)
            packages = find_packages(locator, pkg, versions)
            if packages:
                return packages


class PyPiLocator(locators.SimpleScrapingLocator):
    def __init__(self, url, **kwargs):
        super(PyPiLocator, self).__init__(url, **kwargs)
        self.opener = Pool(maxsize=POOL_MAX_SIZE)

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
            response, final_url = self.opener.retrieve(url)
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


class CurdlingLocator(locators.Locator):

    def __init__(self, url, **kwargs):
        super(CurdlingLocator, self).__init__(**kwargs)
        self.base_url = url
        self.url = url
        self.opener = Pool(maxsize=POOL_MAX_SIZE)
        self.requirements_not_found = []

    def get_distribution_names(self):
        return json.loads(
            self.opener.retrieve(
                compat.urljoin(self.url, 'api'))[0].data)

    def _get_project(self, name):
        # Retrieve the info
        url = compat.urljoin(self.url, 'api/' + name)
        try:
            response, _ = self.opener.retrieve(url)
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
        mdata.source_url = mdata.download_url = source_url['url']

        # Building the dist and associating the download url
        distribution = database.Distribution(mdata)
        distribution.locator = self
        return distribution


class Downloader(Service):

    def __init__(self, *args, **kwargs):
        super(Downloader, self).__init__(*args, **kwargs)
        self.opener = Pool(maxsize=POOL_MAX_SIZE)
        self.locator = get_locator(self.conf)

    def handle(self, requester, requirement, sender_data):
        found = self.find(requirement)
        if found:
            return {"path": self.download(found)}
        raise ReportableError('Requirement `{0}\' not found'.format(
            requirement))

    def get_servers_to_update(self):
        failures = {}
        for locator in self.locator.locators:
            if isinstance(locator, CurdlingLocator) and locator.requirements_not_found:
                failures[locator.base_url] = locator.requirements_not_found
        return failures

    # -- Private API of the Download service --

    def find(self, requirement):
        prereleases = self.conf.get('prereleases', True)

        if not util.parse_requirement(requirement).is_link:
            # We're dealing with the regular requirements: "name (x.y.z)"
            return self.locator.locate(requirement, prereleases)
        else:
            # We're dealing with a link
            mdata = metadata.Metadata(scheme=self.locator.scheme)
            mdata.source_url = mdata.download_url = requirement
            return database.Distribution(mdata)

    def download(self, distribution):
        final_url = url = distribution.download_url

        # We're dealing with a requirement, not a link
        if distribution.locator:
            # The locator's might contain authentication credentials, while the
            # package url might not (cause they got stripped at some point)
            base_url = distribution.locator.base_url
            final_url = update_url_credentials(base_url, url)

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
            raise UnknownProtocol('\n'.join([
                url,
                util.spaces(3, 'Make sure it starts with the right `vcs+` prefix.'),
            ]))

        # Remove the protocol prefix from the url before passing to the handler
        # which is not prepared to handle urls starting with `vcs+`.
        return protocol_mapping[handler](re.sub('[^\+]+\+', '', final_url))

    def _download_http(self, url):
        response, _ = self.opener.retrieve(url)
        if response.status != 200:
            raise ReportableError(
                'Failed to download url `{0}\': {1} ({2})'.format(
                    url,
                    response.status,
                    compat.httplib.responses[response.status],
                ))

        # Now that we're sure that our request was successful
        header = response.headers.get('content-disposition', '')
        file_name = re.findall(r'filename=([^;]+)', header)
        return self.index.from_data(
            file_name and file_name[0] or url,
            response.read(cache_content=True, decode_content=False))

    def _download_git(self, url):
        destination = tempfile.mkdtemp()
        util.execute_command('git', 'clone', url, destination)
        return destination

    def _download_hg(self, url):
        destination = tempfile.mkdtemp()
        util.execute_command('hg', 'clone', url, destination)
        return destination

    def _download_svn(self, url):
        destination = tempfile.mkdtemp()
        util.execute_command('svn', 'co', url, destination)
        return destination
