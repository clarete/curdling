from __future__ import absolute_import, unicode_literals, print_function
from pkg_resources import Requirement
from mock import call, patch, Mock

import os
import errno
import pkg_resources

from curdling import Env
from curdling.index import Index
from curdling.util import expand_requirements, gen_package_path


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


def test_gen_package_path():
    "Utility to generate a sub-path for a package given its name"

    # Given the following package
    package = 'gherkin==0.1.0'

    # When I request a new name
    dir_name = gen_package_path(package)

    # Then I see the right directory structure
    dir_name.should.equal(os.path.join('g', 'h', 'gherkin'))


@patch('curdling.pkg_resources.get_distribution')
def test_check_installed(get_distribution):
    "It should be possible to check if a certain package is currently installed"

    get_distribution.return_value = True
    Env().check_installed('gherkin==0.1.0').should.be.true

    get_distribution.side_effect = pkg_resources.VersionConflict
    Env().check_installed('gherkin==0.1.0').should.be.false

    get_distribution.side_effect = pkg_resources.DistributionNotFound
    Env().check_installed('gherkin==0.1.0').should.be.false


def test_request_install_no_cache():
    "Request the installation of a package when there is no cache"

    # Given that I have an environment
    index = Mock()
    index.find.return_value = []
    env = Env(conf={'index': index})
    env.check_installed = Mock(return_value=False)
    env.services['download'] = Mock()

    # When I request an installation of a package
    env.request_install('gherkin==0.1.0')

    # Then I see that the caches were checked
    env.check_installed.assert_called_once_with('gherkin==0.1.0')
    list(env.index.find.call_args_list).should.equal([
        call('gherkin==0.1.0', only=('whl',)),
        call('gherkin==0.1.0', only=('gz', 'bz', 'zip')),
    ])

    # And then I see that the download queue was populated
    env.services['download'].queue.assert_called_once_with('gherkin==0.1.0')


def test_request_install_installed_package():
    "Request the installation of an already installed package"

    # Given that I have an environment
    index = Mock()
    index.find.return_value = []
    env = Env(conf={'index': index})
    env.check_installed = Mock(return_value=True)
    env.services['download'] = Mock()

    # When I request an installation of a package
    env.request_install('gherkin==0.1.0').should.be.true

    # Then I see that, since the package was installed, the local cache was not
    # queried
    env.check_installed.assert_called_once_with('gherkin==0.1.0')
    env.index.find.called.should.be.false

    # And then I see that the download queue was not touched
    env.services['download'].queue.called.should.be.false


def test_request_install_cached_package():
    "Request the installation of a cached package"

    # Given that I have a loaded local cache
    index = Index('')
    index.storage = {'gherkin==0.1.0': ['storage1/gherkin-0.1.0.tar.gz']}

    # And that I have an environment associated with that local cache
    env = Env(conf={'index': index})
    env.check_installed = Mock(return_value=False)
    env.services['download'] = Mock()
    env.services['install'] = Mock()
    env.services['curdling'] = Mock()

    # When I request an installation of a package
    env.request_install('gherkin==0.1.0').should.be.false

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
    index.storage = {'gherkin==0.1.0': ['storage1/gherkin-0.1.0-py27-none-any.whl']}

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


def test_index_find():
    "It should be possible to find indexed packages"

    index = Index('')

    index.storage = {'gherkin==0.1.0': ['storage1/gherkin-0.1.0.tar.gz']}
    index.find('gherkin==0.1.0', only=('gz',)).should.have.length_of(1)
    index.find('gherkin==0.1.0', only=('whl',)).should.be.empty


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
