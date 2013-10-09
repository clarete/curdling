from __future__ import absolute_import, print_function, unicode_literals
from mock import call, patch, Mock
from nose.tools import nottest

from curdling.index import Index, PackageNotFound
from curdling.install import Install


def test_request_install_no_cache():
    "Request the installation of a package when there is no cache"

    # Given that I have an environment
    index = Mock()
    index.get.side_effect = PackageNotFound('gherkin==0.1.0', 'whl')
    env = Install(conf={'index': index})
    env.start_services()
    env.database.check_installed = Mock(return_value=False)
    env.downloader = Mock()

    # When I request an installation of a package
    env.request_install('main', 'gherkin==0.1.0')

    # Then I see that the caches were checked
    env.database.check_installed.assert_called_once_with('gherkin==0.1.0')

    list(env.index.get.call_args_list).should.equal([
        call('gherkin==0.1.0;whl'),
        call('gherkin==0.1.0;~whl'),
    ])

    # And then I see that the download queue was populated
    env.downloader.queue.assert_called_once_with('main', 'gherkin==0.1.0')


def test_request_install_installed_package():
    "Request the installation of an already installed package"

    # Given that I have an environment
    index = Mock()
    env = Install(conf={'index': index})
    env.start_services()
    env.database.check_installed = Mock(return_value=True)
    env.downloader = Mock()

    # When I request an installation of a package
    env.request_install('main', 'gherkin==0.1.0').should.be.true

    # Then I see that, since the package was installed, the local cache was not
    # queried
    env.database.check_installed.assert_called_once_with('gherkin==0.1.0')
    env.index.get.called.should.be.false

    # And then I see that the download queue was not touched
    env.downloader.queue.called.should.be.false


def test_request_install_cached_package():
    "Request the installation of a cached package"

    # Given that I have a loaded local cache
    index = Index('')
    index.storage = {'gherkin': {'0.1.0': ['storage1/gherkin-0.1.0.tar.gz']}}

    # And that I have an environment associated with that local cache
    env = Install(conf={'index': index})
    env.start_services()
    env.database.check_installed = Mock(return_value=False)
    env.downloader = Mock()
    env.installer = Mock()
    env.curdler = Mock()

    # When I request an installation of a package
    env.request_install('main', 'gherkin==0.1.0')

    # Then I see that, since the package was not installed, the locall cache
    # was queried and returned the right entry
    env.database.check_installed.assert_called_once_with('gherkin==0.1.0')

    # And I see that the install queue was populated
    env.curdler.queue.assert_called_once_with(
        'main', 'gherkin==0.1.0', path='storage1/gherkin-0.1.0.tar.gz')

    # And that the download queue was not touched
    env.downloader.queue.called.should.be.false
    env.installer.queue.called.should.be.false


@nottest
def test_request_install_cached_wheels():
    "Request the installation of a cached package"

    # Given that I have a loaded local cache
    index = Index('')
    index.storage = {'gherkin': {'0.1.0': ['storage1/gherkin-0.1.0-py27-none-any.whl']}}

    # And that I have an environment associated with that local cache
    env = Install(conf={'index': index})
    env.check_installed = Mock(return_value=False)
    env.services['download'] = Mock()
    env.services['install'] = Mock()

    # When I request an installation of a package
    env.request_install('gherkin==0.1.0').should.be.false

    # Then I see that, since the package was not installed, the locall cache
    # was queried and returned the right entry
    env.check_installed.assert_called_once_with('gherkin==0.1.0')

    # And I see that the install queue was populated
    env.services['install'].queue.assert_called_once_with(
        'gherkin==0.1.0', 'main', path='storage1/gherkin-0.1.0-py27-none-any.whl')

    # And that the download queue was not touched
    env.services['download'].queue.called.should.be.false
