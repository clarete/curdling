from __future__ import absolute_import, print_function, unicode_literals
from mock import Mock, ANY
from nose.tools import nottest
import os
import errno

from curdling import util
from curdling.exceptions import ReportableError
from curdling.index import Index
from curdling.install import Install
from curdling.database import Database

from curdling.services.base import Service
from curdling.services.downloader import Downloader
from curdling.services.curdler import Curdler
from curdling.services.installer import Installer

from . import FIXTURE


def test_service():
    "Service#_worker() should stop when hitting the sentinel"

    # Given the following service
    class MyService(Service):
        pass

    callback = Mock()
    service = MyService()
    service.connect('failed', callback)

    # When I queue one package to be processed than I queue the stop sentinel
    service.queue('main', 'package')
    service.queue(None, None)
    service._worker()

    # Then I see that the package is indeed processed but the service dies
    # properly when it receives the sentinel.
    callback.assert_called_once_with('myservice', 'package', path=ANY)

    # And that in the `path` parameter we receive an exception (Unfortunately
    # we can't compare NotImplementedError() instances :(
    callback.call_args_list[0][1]['path'].message.should.equal(
        'The service subclass should override this method'
    )


def test_service_success():
    "Service#_worker() should execute self#handler() method successfully"

    # Given the following service
    class MyService(Service):
        def handle(self, requester, package, sender_data):
            return {'package': 'processed-package'}

    callback = Mock()
    service = MyService()
    service.connect('finished', callback)

    # When I queue one package to be processed than I queue the stop sentinel
    service.queue('main', 'package')
    service.queue(None, None)
    service._worker()

    # Then I see that the right signal was emitted
    callback.assert_called_once_with(
        'myservice', 'package', package='processed-package')


def test_downloader_with_no_sources():
    "It should be possible to download packages from pip repos with no sources"

    # Given the following downloader component with NO SOURCES
    downloader = Downloader(**{'index': Index('')})

    # When I try to retrieve a package from it, than I see it just blows up
    # with a nice exception
    downloader.handle.when.called_with(
        'main', 'gherkin==0.1.0', {}).should.throw(ReportableError)


def test_downloader():
    "It should be possible to download packages from pip repos"

    # Given the following downloader component associated with a temporary
    # index
    index = Index(FIXTURE('tmpindex'))
    downloader = Downloader(**{
        'index': index,
        'conf': {
            'pypi_urls': ['http://localhost:8000/simple'],
        },
    })

    # When I try to retrieve a package from it
    package = downloader.handle('main', 'gherkin (== 0.1.0)', {})

    # Then I see that the package was downloaded correctly to the storage
    index.get('gherkin==0.1.0').should_not.be.empty

    # And I cleanup the mess
    index.delete()


def test_downloader_hyphen_on_pkg_name():
    "The Downloader() service should be able to locate packages with hyphens on the name"

    # Given the following downloader component associated with a temporary
    # index
    index = Index(FIXTURE('tmpindex'))
    downloader = Downloader(**{
        'index': index,
        'conf': {
            'pypi_urls': ['http://localhost:8000/simple'],
        },
    })

    # When I try to retrieve a package from it
    package = downloader.handle('main', 'fake-pkg (== 0.0.0)', {})

    # Then I see that the package was downloaded correctly to the storage
    index.get('fake-pkg (== 0.0.0)').should_not.be.empty

    # And I cleanup the mess
    index.delete()


def test_downloader_underscore_on_pkg_name():
    "The Downloader() service should be able to locate packages with underscores on the name"

    # Given the following downloader component associated with a temporary
    # index
    index = Index(FIXTURE('tmpindex'))
    downloader = Downloader(**{
        'index': index,
        'conf': {
            'pypi_urls': ['http://localhost:8000/simple'],
        },
    })

    # When I try to retrieve a package from it
    package = downloader.handle('main', 'fake_pkg (== 0.0.0)', {})

    # Then I see that the package was downloaded correctly to the storage
    index.get('fake_pkg (== 0.0.0)').should_not.be.empty

    # And I cleanup the mess
    index.delete()


def test_downloader_with_no_packages():
    "After downloading packages, the result queue should be fed"

    # Given the following downloader component associated with a temporary
    # index
    index = Index(FIXTURE('tmpindex'))
    downloader = Downloader(**{
        'index': index,
        'conf': {
            'pypi_urls': ['http://localhost:8000/simple'],
        },
    })

    # When I try to retrieve a package from it
    downloader.handle.when.called_with(
        'main', 'donotexist==0.1.0', {}).should.throw(ReportableError,
            'Package `donotexist==0.1.0\' not found')


def test_curd_package():
    "It should possible to convert regular packages to wheels"

    # Given that I have a storage containing a package
    index = Index(FIXTURE('storage1'))
    index.scan()

    # And a curdling using that index
    curdling = Curdler(**{'index': index})

    # When I request a curd to be created
    package = curdling.handle('main', 'gherkin==0.1.0', {
        'path': index.get('gherkin==0.1.0;~whl')})

    # Then I see it's a wheel package.
    package.should.equal({
        'path': FIXTURE('storage1/gherkin-0.1.0-py27-none-any.whl'),
    })

    # And that it's present in the index
    package = index.get('gherkin==0.1.0;whl')

    # And that the file was created in the file system
    os.path.exists(package).should.be.true

    # And I delete the file
    os.unlink(package)


def test_install_package():
    "It should possible to install wheels"

    # Given that I have an installer configured with a loaded index
    index = Index(FIXTURE('storage2'))
    index.scan()
    installer = Installer(**{'index': index})

    # When I request a curd to be created
    installer.handle('main', 'gherkin==0.1.0', {
        'path': index.get('gherkin==0.1.0;whl')})

    # Then I see that the package was installed
    Database.check_installed('gherkin==0.1.0').should.be.true

    # And I uninstall the package
    Database.uninstall('gherkin==0.1.0')
