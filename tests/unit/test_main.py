from __future__ import absolute_import, unicode_literals, print_function
from pkg_resources import Requirement
from mock import patch, Mock

import os
import errno
import pkg_resources

from curdling.core import LocalCache, Env
from curdling.download import DirectoryStorage
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


@patch('curdling.core.pkg_resources.get_distribution')
def test_check_installed(get_distribution):
    "It should be possible to check if a certain package is currently installed"

    get_distribution.return_value = True
    Env(cache_backend={}).check_installed('gherkin==0.1.0').should.be.true

    get_distribution.side_effect = pkg_resources.VersionConflict
    Env(cache_backend={}).check_installed('gherkin==0.1.0').should.be.false

    get_distribution.side_effect = pkg_resources.DistributionNotFound
    Env(cache_backend={}).check_installed('gherkin==0.1.0').should.be.false


def test_local_cache_search():
    "Local cache should be able to tell if a given package is present or not"

    # Given that I have an instance of our local cache with a package indexed
    cache = LocalCache(backend={})
    cache.put('gherkin==0.1.0', 'gherkin package path')

    # When I look for the requirement
    path = cache.get('gherkin==0.1.0')

    # Then I see that the package exists
    path.should.equal('gherkin package path')


def test_directory_storage_permission_denied():
    "DirectoryStorage.build_path() should handle other kinds of IOError exceptions"

    with patch('os.makedirs') as makedirs:
        exc = OSError()
        exc.errno = errno.EPERM
        makedirs.side_effect = exc

        (DirectoryStorage('/root').build_path
         .when.called_with('sub-directory')
         .should.throw(OSError))


def test_request_install_no_cache():
    "Request the installation of a package when there is no cache"

    # Given that I have an environment
    cache = Mock()
    cache.get.return_value = None
    env = Env(cache_backend=cache)
    env.check_installed = Mock(return_value=False)
    env.download_manager = Mock()

    # When I request an installation of a package
    env.request_install('gherkin==0.1.0')

    # Then I see that the caches were checked
    env.check_installed.assert_called_once_with('gherkin==0.1.0')
    env.local_cache.backend.get.assert_called_once_with('gherkin==0.1.0')

    # And then I see that the download queue was populated
    env.download_manager.queue.assert_called_once_with('gherkin==0.1.0')


def test_request_install_installed_package():
    "Request the installation of an already installed package"

    # Given that I have an environment
    cache = Mock()
    env = Env(cache_backend=cache)
    env.check_installed = Mock(return_value=True)
    env.download_manager = Mock()

    # When I request an installation of a package
    env.request_install('gherkin==0.1.0').should.be.true

    # Then I see that, since the package was installed, the local cache was not
    # queried
    env.check_installed.assert_called_once_with('gherkin==0.1.0')
    env.local_cache.backend.get.called.should.be.false

    # And then I see that the download queue was not touched
    env.download_manager.queue.called.should.be.false


def test_request_install_cached_package():
    "Request the installation of a cached package"

    # Given that I have a loaded local cache
    cache = {'gherkin==0.1.0': gen_package_path('gherkin==0.1.0')}

    # And that I have an environment associated with that local cache
    env = Env(cache_backend=cache)
    env.check_installed = Mock(return_value=False)
    env.download_manager = Mock()
    env.install_manager = Mock()

    # When I request an installation of a package
    env.request_install('gherkin==0.1.0').should.be.false

    # Then I see that, since the package was not installed, the locall cache
    # was queried and returned the right entry
    env.check_installed.assert_called_once_with('gherkin==0.1.0')

    # And I see that the install queue was populated
    env.install_manager.queue.assert_called_once_with('gherkin==0.1.0')

    # And that the download queue was not touched
    env.download_manager.queue.called.should.be.false
