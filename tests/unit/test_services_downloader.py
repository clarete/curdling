#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from mock import Mock, patch
from distlib import database

from curdling.services import downloader


class TestPyPiLocator(downloader.PyPiLocator):
    def __init__(self, *args, **kw):
        super(TestPyPiLocator, self).__init__(*args, **kw)
        self.opener = Mock()


class TestPool(downloader.Pool):
    def __init__(self, response):
        self.response = response

    def request(self,  method, url, **params):
        response = self.response
        response.params = params
        response.method = method
        response.url = url
        return response


@patch('curdling.services.downloader.distlib')
def test_find_packages(distlib):
    ("find_packages should use the scheme from the "
     "locator to match the best result")
    # Background
    # The scheme is mocked
    scheme = distlib.version.get_scheme.return_value
    # As well as the matcher
    matcher = scheme.matcher.return_value
    # And a version class
    version_class = matcher.version_class.return_value

    # Given a locator
    locator = Mock()

    # And a requirement
    requirement = Mock()

    # And a versions dictionary
    distribution = Mock()
    versions = {
        '1.0': distribution
    }

    # When I invoke find_packages
    result = downloader.find_packages(locator, requirement, versions)
    # Then the result should be the expected distribution
    result.should.equal(distribution)
    # And the method calls should be correct (sorry for this sad test,
    # I'm still getting to know the codebase)
    matcher.match.assert_called_once_with(version_class)
    scheme.matcher.assert_called_once_with(requirement.requirement)
    distlib.version.get_scheme.assert_called_once_with(locator.scheme)


def test_update_url_credentials():
    "update_url_credentials() should update URL2 using auth info from URL1"

    # Given that I have a URL with authentication info
    url1 = 'http://user:almost-safe-password@domain.com/path/to/resource.html'

    # And another URL without auth info
    url2 = 'http://domain.com/another/path/to/a/cooler/resource.html'

    # When I update the second one based on the first one
    final_url = downloader.update_url_credentials(url1, url2)

    # Then I see that the final URL version is just the second URL with the auth
    # info from the first one
    final_url.should.equal(
        'http://user:almost-safe-password@domain.com/another/path/to/a/cooler/resource.html')


def test_update_url_credentials_not_from_the_same_server():
    "update_url_credentials() Should just use the second URL if the URLS are pointing to different services"

    # Given that I have a URL with authentication info from domain1.com
    url1 = 'http://user:passwd@domain1.com/resource1.html'

    # And another URL without auth info from domain2.com
    url2 = 'http://domain2.com/resource2.html'

    # When I update the second one based on the first one
    final_url = downloader.update_url_credentials(url1, url2)

    # Then I see that the final URL is just a copy of the second URL
    final_url.should.equal(url2)


@patch('curdling.services.downloader.util')
def test_pool_retrieve_no_redirect(util):
    ("Pool#retrieve should make a request and return a tuple "
     "containing the response and the actual url of the retrieved resource")

    # Background:
    # util.get_auth_info_from_url returns a fake dictionary
    util.get_auth_info_from_url.return_value = {'foo': 'bar'}

    # Given a mocked response
    response = Mock()
    response.get_redirect_location.return_value = None

    # When I retrieve a URL
    pool = TestPool(response)
    response, url = pool.retrieve('http://github.com')

    # Then the url should be the same as requested
    url.should.equal('http://github.com')

    # And the response should be the mocked one
    response.should.be.property("params").being.equal({u'headers': {'foo': 'bar'}, u'preload_content': False})
    response.should.be.property("method").being.equal("GET")
    response.should.be.property("url").being.equal("http://github.com")
    util.get_auth_info_from_url.assert_called_once_with('http://github.com')


@patch('curdling.services.downloader.util')
def test_pool_retrieve(util):
    ("Pool#retrieve should follows the redirect and "
     "returns the action resource url")
    # Background:
    # util.get_auth_info_from_url returns a fake dictionary
    util.get_auth_info_from_url.return_value = {'foo': 'bar'}

    # Given a mocked response
    response = Mock()
    response.get_redirect_location.return_value = "http://bitbucket.com"

    # When I retrieve a URL
    pool = TestPool(response)
    response, url = pool.retrieve('http://github.com')

    # Then the url should be the same as requested
    url.should.equal('http://bitbucket.com')

    # And the response should be the mocked one
    response.should.be.property("params").being.equal({u'headers': {'foo': 'bar'}, u'preload_content': False})
    response.should.be.property("method").being.equal("GET")
    response.should.be.property("url").being.equal("http://github.com")
    util.get_auth_info_from_url.assert_called_once_with('http://github.com')



@patch('curdling.services.downloader.util')
@patch('curdling.services.downloader.find_packages')
def test_aggregating_locator_locate(find_packages, util):
    ("AggregatingLocator#locate should return the first package "
     "that matches the given version")
    # Background:

    # parse_requirement is mocked and will return a mocked pkg
    pkg = util.parse_requirement.return_value

    # find_packages will return a package right away
    find_packages.return_value = 'the awesome "foo" package :)'


    # Specification:

    # Given a mocked locator
    locator = Mock()

    # And that the AggregatingLocator has a list containing that one locator
    class TestLocator(downloader.AggregatingLocator):
        def __init__(self):
            self.locators = [locator]

    # And an instance of AggregatingLocator
    instance = TestLocator()

    # When I try to locate a package with certain requirement
    found = instance.locate("foo==1.1.1")

    # Then it should be the expected package
    found.should.equal('the awesome "foo" package :)')


def test_pypilocator_get_project():
    ("PyPiLocator#_get_project should fetch based on the base_url")
    # Given an instance of PyPiLocator that mocks out the _fetch method
    instance = TestPyPiLocator("http://github.com")
    instance._fetch = Mock()

    # When _get_project gets called
    response = instance._get_project("forbiddenfruit")

    # Then it should have called _fetch
    instance._fetch.assert_called_once_with(
        u'http://github.com/forbiddenfruit/',
        u'forbiddenfruit',
    )


def test_visit_link_when_platform_dependent():
    ("PyPiLocator#_visit_link() should return (None, None) "
     "if link is platform dependent")

    # Given an instance of PyPiLocator
    instance = TestPyPiLocator("http://github.com")
    # And that calling _is_platform_dependent will return True
    instance._is_platform_dependent = Mock(return_value=True)

    # When I call _visit_link
    result = instance._visit_link("github", "some-link")

    # Then it should be a tuple with 2 `None` items
    result.should.equal((None, None))


def test_visit_link_when_not_platform_dependent():
    ("PyPiLocator#_visit_link() should return ('package-name', 'version') "
     "when link is not platform dependent")

    # Given an instance of PyPiLocator that mocks out the expected
    # private method calls
    class PyPiLocatorMock(TestPyPiLocator):
        _is_platform_dependent = Mock(return_value=False)
        def convert_url_to_download_info(self, link, project_name):
            return "HELLO, I AM A PROJECT INFO"

        def _update_version_data(self, versions, info):
            versions['sure'] = '4.0'
            info.should.equal('HELLO, I AM A PROJECT INFO')

    # And an instance of the locator
    instance = PyPiLocatorMock('http://curdling.io')

    # When I call _visit_link
    result = instance._visit_link('package-name', 'some-link')

    # Then it should be a tuple with 2
    result.should.equal(('sure', '4.0'))


def test_pypilocator_fetch_when_page_is_falsy():
    ("PyPiLocator#_fetch() should return empty if "
     "get_page returns a falsy value")

    # Given an instance of PyPiLocator that mocks the get_page method
    # so it returns None
    class PyPiLocatorMock(TestPyPiLocator):
        get_page = Mock(return_value=None)

    # And an instance of the locator
    instance = PyPiLocatorMock('http://curdling.io')

    # When I try to fetch a url
    response = instance._fetch('http://somewhere.com/package', 'some-name')

    # Then it should be an empty dictionary
    response.should.be.a(dict)
    response.should.be.empty


def test_pypilocator_fetch_when_page_links_are_falsy():
    ("PyPiLocator#_fetch() should return empty if "
     "get_page returns a page with no links")

    # Given a page that has no links
    page = Mock(links=[])

    # And that PyPiLocator#get_page returns that page
    class PyPiLocatorMock(TestPyPiLocator):
        get_page = Mock(return_value=page)

    # And an instance of the locator
    instance = PyPiLocatorMock('http://curdling.io')

    # When I try to fetch a url
    response = instance._fetch('http://somewhere.com/package', 'some-name')

    # Then it should be an empty dictionary
    response.should.be.a(dict)
    response.should.be.empty


def test_pypilocator_fetch_when_not_seen():
    ("PyPiLocator#_fetch() should visit an unseen link and "
     "grab its distribution into a dict")

    # Given a page that has one link
    page = Mock(links=[('http://someserver.com/package.tgz', 'some-rel')])

    # Given an instance of PyPiLocator that mocks the get_page method
    # to return a page with no links
    class PyPiLocatorMock(TestPyPiLocator):
        get_page = Mock(return_value=page)
        _visit_link = Mock(return_value=('0.0.1', 'distribution'))

    # And an instance of the locator
    instance = PyPiLocatorMock('http://curdling.io')

    # When I try to fetch a url
    response = instance._fetch('http://somewhere.com/package', 'some-name')

    # Then it should equal the existing distribution
    response.should.equal({
        '0.0.1': 'distribution'
    })


def test_downloader_find_deal_with_links():
    "Downloader#find() should know if a requirement is a link and create a downloadable distro for it"

    # Given that I have a Downloader instance
    service = downloader.Downloader()

    # When I try to find a link
    distribution = service.find('http://host/path/package-0.1.zip')

    # Then I see that the distribution was built with the right meta data
    distribution.metadata.source_url.should.equal(
        'http://host/path/package-0.1.zip')


def test_downloader_find_deal_with_packages():
    "Downloader#find() should know if a requirement points to a package and, if so, try to find it with a locator"

    # Given that I have a Downloader instance
    service = downloader.Downloader()
    service.locator = Mock()
    service.locator.locate.return_value = '<The-Package>'

    # When I try to find a package
    distribution = service.find('package (0.1)')

    # Then I see that #find() called the locate method of the locator
    distribution.should.equal('<The-Package>')
