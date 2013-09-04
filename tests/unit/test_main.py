from __future__ import absolute_import, unicode_literals, print_function
from pkg_resources import Requirement
from mock import call, patch, Mock

import os
import errno
import pkg_resources

from curdling import Env
from curdling.index import Index, PackageNotFound
from curdling.util import expand_requirements
from curdling.service import Service


@patch('io.open')
def test_expand_requirements(open_func):
    "It should be possible to include other files inside"

    # Given that I have two files, called `development.txt` and
    # `requirements.txt` with the following content:
    open_func.return_value.read.side_effect = (
        '-r requirements.txt\nsure==0.2.1\n',  # development.txt
        'gherkin==0.1.0\n\n\n',                # requirements.txt
    )

    # When I expand the requirements
    requirements = expand_requirements('development.txt')

    # Then I see that all the required files were retrieved
    requirements.should.equal([
        Requirement.parse('gherkin==0.1.0'),
        Requirement.parse('sure==0.2.1'),
    ])


@patch('curdling.pkg_resources.get_distribution')
def test_check_installed(get_distribution):
    "It should be possible to check if a certain package is currently installed"

    get_distribution.return_value = True
    Env({}).check_installed('gherkin==0.1.0').should.be.true

    get_distribution.side_effect = pkg_resources.VersionConflict
    Env({}).check_installed('gherkin==0.1.0').should.be.false

    get_distribution.side_effect = pkg_resources.DistributionNotFound
    Env({}).check_installed('gherkin==0.1.0').should.be.false


def test_service_subscribe():
    "Services should be able to subscribe to other services"

    # Given that I have two services
    service1 = Service(lambda p: '1')
    service2 = Service(lambda p: '2')

    # When I subscribe one service to another
    service1.subscribe(service2)
    service2.queue('gherkin==0.1.0')
    service2.consume()
    service2.pool.join()

    # Then I see that service1 was notified
    service2.subscribers[0].package_queue.qsize().should.equal(1)


def test_request_install_no_cache():
    "Request the installation of a package when there is no cache"

    # Given that I have an environment
    index = Mock()
    index.get.side_effect = PackageNotFound('gherkin==0.1.0', 'whl')
    env = Env(conf={'index': index})
    env.check_installed = Mock(return_value=False)
    env.services['download'] = Mock()

    # When I request an installation of a package
    env.request_install('gherkin==0.1.0')

    # Then I see that the caches were checked
    env.check_installed.assert_called_once_with('gherkin==0.1.0')
    list(env.index.get.call_args_list).should.equal([
        call('gherkin==0.1.0;whl'),
        call('gherkin==0.1.0;~whl'),
    ])

    # And then I see that the download queue was populated
    env.services['download'].queue.assert_called_once_with('gherkin==0.1.0')


def test_request_install_installed_package():
    "Request the installation of an already installed package"

    # Given that I have an environment
    index = Mock()
    env = Env(conf={'index': index})
    env.check_installed = Mock(return_value=True)
    env.services['download'] = Mock()

    # When I request an installation of a package
    env.request_install('gherkin==0.1.0').should.be.true

    # Then I see that, since the package was installed, the local cache was not
    # queried
    env.check_installed.assert_called_once_with('gherkin==0.1.0')
    env.index.get.called.should.be.false

    # And then I see that the download queue was not touched
    env.services['download'].queue.called.should.be.false


def test_request_install_cached_package():
    "Request the installation of a cached package"

    # Given that I have a loaded local cache
    index = Index('')
    index.storage = {'gherkin': {'0.1.0': ['storage1/gherkin-0.1.0.tar.gz']}}

    # And that I have an environment associated with that local cache
    env = Env(conf={'index': index})
    env.check_installed = Mock(return_value=False)
    env.services['download'] = Mock()
    env.services['install'] = Mock()
    env.services['curdling'] = Mock()

    # When I request an installation of a package
    env.request_install('gherkin==0.1.0')

    # Then I see that, since the package was not installed, the locall cache
    # was queried and returned the right entry
    env.check_installed.assert_called_once_with('gherkin==0.1.0')

    # And I see that the install queue was populated
    env.services['curdling'].queue.assert_called_once_with('gherkin==0.1.0')

    # And that the download queue was not touched
    env.services['download'].queue.called.should.be.false
    env.services['install'].queue.called.should.be.false


def test_request_install_cached_wheels():
    "Request the installation of a cached package"

    # Given that I have a loaded local cache
    index = Index('')
    index.storage = {'gherkin': {'0.1.0': ['storage1/gherkin-0.1.0-py27-none-any.whl']}}

    # And that I have an environment associated with that local cache
    env = Env(conf={'index': index})
    env.check_installed = Mock(return_value=False)
    env.services['download'] = Mock()
    env.services['install'] = Mock()

    # When I request an installation of a package
    env.request_install('gherkin==0.1.0').should.be.false

    # Then I see that, since the package was not installed, the locall cache
    # was queried and returned the right entry
    env.check_installed.assert_called_once_with('gherkin==0.1.0')

    # And I see that the install queue was populated
    env.services['install'].queue.assert_called_once_with('gherkin==0.1.0')

    # And that the download queue was not touched
    env.services['download'].queue.called.should.be.false


@patch('curdling.index.os')
def test_index_ensure_path(patched_os):
    "Test utility method Index.ensure_path()"

    # We'll need that inside of ensure_path()
    patched_os.path.dirname = os.path.dirname

    # Given that I have an index
    index = Index('')

    # When I call ensure_path(resource) against a directory that doesn't seem
    # to exist, it should try to create the directory for the resource
    patched_os.path.isdir.return_value = False
    index.ensure_path('path/to/my/resource')
    patched_os.makedirs.assert_called_once_with('path/to/my')


@patch('curdling.index.os')
def test_index_ensure_path_for_existing_dirs(patched_os):
    "Test utility method Index.ensure_path() for existing directories"

    # We'll need that inside of ensure_path()
    patched_os.path.dirname = os.path.dirname

    # Given that I have an index
    index = Index('')

    # When I call ensure_path(resource) against a directory that exists to
    # exists, it *SHOULD NOT* try to create the directory
    patched_os.path.isdir.return_value = True
    index.ensure_path('path/to/my/resource')
    patched_os.makedirs.called.should.be.false


def test_index_feed_backend():
    "It should be possible to save package paths granularly"

    # Given the following index
    index = Index('')

    # When I index a couple files
    index.index('http://localhost:800/p/gherkin-0.1.0-py27-none-any.whl')
    index.index('gherkin-0.1.0.tar.gz')
    index.index('Gherkin-0.1.5.tar.gz')  # I know, weird right?
    index.index('a/weird/dir/gherkin-0.2.0.tar.gz')

    # Then I see that the backend structure looks right
    dict(index.storage).should.equal({
        'gherkin': {
            '0.2.0': [
                'gherkin-0.2.0.tar.gz',
            ],
            '0.1.5': [
                'Gherkin-0.1.5.tar.gz',
            ],
            '0.1.0': [
                'gherkin-0.1.0-py27-none-any.whl',
                'gherkin-0.1.0.tar.gz',
            ],
        },
    })


def test_index_get():
    "It should be possible to search for packages using different criterias"

    # Given that I have an index loaded with a couple package references
    index = Index('')
    index.storage = {
        'gherkin': {
            '0.2.0': [
                'gherkin-0.2.0.tar.gz',
            ],
            '0.1.5': [
                'gherkin-0.2.0.tar.gz',
            ],
            '0.1.1': [
                'gherkin-0.1.1.tar.gz',
            ],
            '0.1.0': [
                'gherkin-0.1.0.tar.gz',
                'gherkin-0.1.0-py27-none-any.whl',
            ],
        }
    }

    # Let's do some random assertions

    # No version: Always brings the newest
    index.get('gherkin').should.equal('gherkin-0.2.0.tar.gz')

    # With a range of versions: Always brings the newest
    index.get('gherkin>0.1.0').should.equal('gherkin-0.2.0.tar.gz')

    # With a handful of version specs: Find the matching version and prefer whl
    index.get('gherkin>=0.1.0,<0.1.5,!=0.1.1').should.equal('gherkin-0.1.0-py27-none-any.whl')

    # With version: Always prefers the wheel
    index.get('gherkin==0.1.0,<=0.2.0').should.equal('gherkin-0.1.0-py27-none-any.whl')

    # With version and format: Prefers anything but `whl'
    index.get('gherkin==0.1.0;~whl').should.equal('gherkin-0.1.0.tar.gz')

    # With version range and no format: Finds the highest version with the :)
    index.get.when.called_with('gherkin==0.1.1;whl').should.throw(
        PackageNotFound, (
            "The index does not have the requested package: "
            "gherkin==0.1.1 (whl)"))

    # With version and a format that is not available: Blows up! :)
    index.get.when.called_with('gherkin==0.1.1;whl').should.throw(
        PackageNotFound, (
            "The index does not have the requested package: "
            "gherkin==0.1.1 (whl)"))

    # With a version we simply don't have: Blows up! :)
    index.get.when.called_with('gherkin==0.2.1').should.throw(
        PackageNotFound, (
            "The index does not have the requested package: "
            "gherkin==0.2.1"))

    # With a package we simply don't have: Blows up! :)
    index.get.when.called_with('nonexisting==0.2.1').should.throw(
        PackageNotFound, (
            "The index does not have the requested package: "
            "nonexisting==0.2.1"))


def test_index_get_corner_case_pkg_name():
    "It should be possible to search for packages that contain `_` in their name"

    # Given that I have an index loaded with a couple package references
    index = Index('')
    index.storage = {
        'python-gherkin': {
            '0.1.0': [
                'python_gherkin-0.1.0.tar.gz',
            ]
        }
     }


    index.get('python-gherkin==0.1.0;~whl').should.equal('python_gherkin-0.1.0.tar.gz')
