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


@nottest
def test_service_failure():
    "Service() should handle custom callback failures"

    # Given the following service
    class MyService(Service):
        def __init__(self, result_queue=None):
            super(MyService, self).__init__(
                callback=self.run,
                result_queue=result_queue,
            )

        def run(self, package, sender_data):
            raise ValueError("I don't want to do anything")

    queue = JoinableQueue()
    service = MyService(result_queue=queue)

    # When I queue a package to be processed by my service and start the
    # service with 1 concurrent worker
    service.queue('gherkin==0.1.0', 'main')
    service.consume()
    service.pool.join()         # Ensure we finish spawning the greenlet

    # Then I see that no package was processed
    queue.qsize().should.equal(0)

    # And that the list of failed packages was updated
    service.failed_queue[0][0].should.equal('gherkin==0.1.0')
    service.failed_queue[0][1].should.be.a(ValueError)
    service.failed_queue[0][1].message.should.equal("I don't want to do anything")


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
