from __future__ import absolute_import, unicode_literals, print_function
from curdling.download import PipSource, DownloadManager, MemoryStorage
from gevent.queue import Queue
from mock import Mock
import os
import errno

from curdling import util, Service, Env, LocalCache
from curdling.download import DirectoryStorage
from curdling.installer import Installer
from curdling.wheelhouse import Curdling

from . import FIXTURE


def test_local_cache_update():
    "It should be possible to update the local cache from a dir full of wheels"

    # Given that I have a local package with an empty dict as its storage
    cache = LocalCache(backend={})

    # When I update the cache()
    cache.scan_dir(FIXTURE('storage2'))

    # Then now we can find the package
    cache.get('gherkin==0.1.0').should.equal(
        'g/h/gherkin/gherkin-0.1.0-py27-none-any.whl')


def test_directory_storage():
    "It should be possible to save files to directories in the local disk"

    # Given the following directory storage
    storage = DirectoryStorage(path=FIXTURE('storagedirtest'))

    # When I save a file to the storage
    storage.write('pkg.txt', 'the content')

    # Then I see that this file exists after the above call
    result_path = FIXTURE('storagedirtest', 'p', 'k', 'pkg', 'pkg.txt')
    os.path.exists(result_path).should.be.true

    # And that the file above has the same content
    open(result_path).read().should.equal('the content')

    # And I clean things up
    storage.delete()


def test_directory_storage_dict_api():
    "The DirectoryStorage component should provide a dict-like API"

    # Given the following directory storage
    storage = DirectoryStorage(path=FIXTURE('storagedirtest1'))

    # When I save a file to the storage
    storage['file.txt'] = 'the content'

    # Then I see that this file exists after the above call
    result_path = FIXTURE('storagedirtest1', 'f', 'i', 'file', 'file.txt')
    os.path.exists(result_path).should.be.true

    # And that the file above has the same content
    open(result_path).read().should.equal('the content')

    # And I delete the whole directory
    storage.delete()


def test_directory_storage_delete_file():
    "It should be possible to delete files from the storage"

    # Given the following directory storage with a file
    storage = DirectoryStorage(path=FIXTURE('storagedirtest2'))
    storage['deleted.txt'] = 'some content'

    # When I blow it up
    os.path.exists(FIXTURE('storagedirtest2/d/e/deleted/deleted.txt')).should.be.true
    del storage['deleted.txt']

    # Then I see the file doesn't exist anymore
    os.path.exists(FIXTURE('storagedirtest2/d/e/deleted/deleted.txt')).should.be.false

    # Removing the storage directory
    storage.delete()


def test_directory_storage_find():
    "The storage should know how to find a package"

    # Given that I have a storage that contains a package
    storage = DirectoryStorage(path=FIXTURE('storage1'))

    # When I try to find this package
    packages = storage.find('gherkin==0.1.0')

    # Then I see that the given package's path was retrieved
    packages.should.equal(['g/h/gherkin/gherkin-0.1.0.tar.gz'])

    # And I see that the content is also right
    storage.read('g/h/gherkin/gherkin-0.1.0.tar.gz').should.equal(
        open(FIXTURE('storage1/g/h/gherkin/gherkin-0.1.0.tar.gz'), 'rb').read())


def test_directory_storage_delete():
    "It should be possible to remove the whole storage"

    # Given the following directory storage (and save a file to create the
    # dirs)
    storage = DirectoryStorage(path=FIXTURE('storagedirtest3'))
    storage['blah'] = 'yo'

    # When I blow it up
    storage.delete()

    # Then I see the file doesn't exist anymore
    os.path.isdir(FIXTURE('storagedirtest3')).should.be.false


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

        def run(self, package):
            self.my_mock.ran = package

    my_mock = Mock()
    queue = Queue()
    service = MyService(my_mock, result_queue=queue)

    # When I queue a package to be processed by my service and start the
    # service with 1 concurrent worker
    service.queue('gherkin==0.1.0')
    service.start(concurrent=1)

    # Then I see that the package processed
    package = queue.get()
    package.should.equal('gherkin==0.1.0')

    my_mock.ran.should.equal('gherkin==0.1.0')


def test_service_failure():
    "Service() should handle custom callback failures"

    # Given the following service
    class MyService(Service):
        def __init__(self, result_queue=None):
            super(MyService, self).__init__(
                callback=self.run,
                result_queue=result_queue,
            )

        def run(self, package):
            raise ValueError("I don't want to do anything")

    queue = Queue()
    service = MyService(result_queue=queue)

    # When I queue a package to be processed by my service and start the
    # service with 1 concurrent worker
    service.queue('gherkin==0.1.0')
    service.start(concurrent=1)
    service.pool.join()         # Ensure we finish spawning the greenlet

    # Then I see that no package was processed
    queue.qsize().should.equal(0)

    # And that the list of failed packages was updated
    service.failed_queue[0][0].should.equal('gherkin==0.1.0')
    service.failed_queue[0][1].should.be.a(ValueError)
    service.failed_queue[0][1].message.should.equal("I don't want to do anything")


def test_downloader():
    "It should be possible to download packages from pip repos"

    # Given the following downloader component
    sources = [PipSource(urls=['http://localhost:8000/simple'])]
    storage = MemoryStorage()
    downloader = DownloadManager(sources=sources, storage=storage)

    # When I try to retrieve a package from it
    package = downloader.retrieve('gherkin==0.1.0')

    # Then I see that the package was downloaded correctly to the storage
    (package in storage).should.be.true


def test_downloader_with_no_packages():
    "After downloading packages, the result queue should be fed"

    # Given the following downloader component
    queue = Mock()
    sources = [PipSource(urls=['http://localhost:8000/simple'])]
    storage = MemoryStorage()
    downloader = DownloadManager(
        sources=sources, storage=storage, result_queue=queue)

    # When I try to retrieve a package from it
    package = downloader.retrieve('donotexist==0.1.0')

    # Then I see package is none :(
    package.should.be.none


def test_curd_package():
    "It should possible to convert regular packages to wheels"

    # Given that I have a storage containing a package
    storage = DirectoryStorage(path=FIXTURE('storage1'))

    # And a curdling using that storage
    curdling = Curdling(storage=storage)

    # When I request a curd to be created
    package = curdling.wheel('gherkin==0.1.0')

    # Then I see it's a wheel package.
    package.should.equal('g/h/gherkin/gherkin-0.1.0-py27-none-any.whl')

    # And that the file was created in the file system
    (os.path.exists(FIXTURE('storage1/g/h/gherkin/gherkin-0.1.0-py27-none-any.whl'))
     .should.be.true)

    # And I delete the file
    del storage[os.path.basename(package)]


def test_install_package():
    "It should possible to install wheels"

    # Given that I have an installer configured with a loaded storage
    storage = DirectoryStorage(path=FIXTURE('storage2'))
    installer = Installer(storage=storage)

    # When I request a curd to be created
    installer.install('gherkin==0.1.0')

    # Then I see that the package was installed
    Env(local_cache_backend={}).check_installed('gherkin==0.1.0').should.be.true

    # And I uninstall the package
    Env(local_cache_backend={}).uninstall('gherkin==0.1.0')
