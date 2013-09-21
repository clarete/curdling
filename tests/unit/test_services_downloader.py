#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from mock import Mock, patch
from curdling.services.downloader import Pool


class TestPool(Pool):
    def __init__(self, response):
        self.response = response

    def request(self,  method, url, **params):
        response = self.response
        response.params = params
        response.method = method
        response.url = url
        return response


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
