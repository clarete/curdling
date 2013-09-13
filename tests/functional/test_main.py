from __future__ import absolute_import, unicode_literals, print_function
from mock import Mock
from nose.tools import nottest
import os
import errno

from curdling import util, Env
from curdling.download import Downloader
from curdling.logging import ReportableError
from curdling.service import Service
from curdling.index import Index
from curdling.installer import Installer
from curdling.wheelhouse import Curdler

from . import FIXTURE


@nottest
def test_service():
    "Service() should implement the basic needs of an async service"

    # Given the following service
    class MyService(Service):
        def __init__(self, my_mock, result_queue=None):
            self.my_mock = my_mock
            super(MyService, self).__init__(
                callback=self.run,
                result_queue=result_queue,
            )

        def run(self, package, sender_data):
            self.my_mock.ran = package

    my_mock = Mock()
    queue = JoinableQueue()
    service = MyService(my_mock, result_queue=queue)

    # When I queue a package to be processed by my service and start the
    # service with 1 concurrent worker
    service.queue('gherkin==0.1.0', 'main')
    service.consume()

    # Then I see that the package processed
    package = queue.get()
    package.should.equal('gherkin==0.1.0')

    my_mock.ran.should.equal('gherkin==0.1.0')


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
    "It should be possible to download packages from pip repos"

    # Given the following downloader component with NO SOURCES
    downloader = Downloader(index=Index(''))

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
            'No distributions found for donotexist==0.1.0')


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
    Env({}).check_installed('gherkin==0.1.0').should.be.true

    # And I uninstall the package
    Env({}).uninstall('gherkin==0.1.0')
