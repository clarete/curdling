from __future__ import absolute_import, unicode_literals, print_function
from curdling.download import PipSource, DownloadManager, MemoryStorage
from gevent.queue import Queue
from mock import Mock


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


def test_downloader_should_feed_result_queue():
    "After downloading packages, the result queue should be fed"

    # Given the following downloader component
    queue = Mock()
    sources = [PipSource(urls=['http://localhost:8000/simple'])]
    storage = MemoryStorage()
    downloader = DownloadManager(
        sources=sources, storage=storage, result_queue=queue)

    # When I try to retrieve a package from it
    package = downloader.retrieve('gherkin==0.1.0')

    # Then I see that the package was downloaded correctly to the storage
    queue.put.assert_called_once_with('g/h/gherkin/gherkin-0.1.0.tar.gz')


def test_downloader_feeds_the_compile_queue():
    "After downloading packages, it should be compiled to a wheel"

    # Given the following downloader component
    queue = Queue()
    storage = MemoryStorage()
    downloader = DownloadManager(
        sources=[PipSource(urls=['http://localhost:8000/simple'])],
        storage=storage, result_queue=queue)

    # When I start the downloader and try to read the next item in the queue
    downloader.queue('gherkin==0.1.0')
    downloader.start(concurrent=1)
    package = queue.get()

    # Then I see that the queue is now empty
    queue.qsize().should.equal(0)

    # And that the package was the one that I requested
    package.should.equal('g/h/gherkin/gherkin-0.1.0.tar.gz')
