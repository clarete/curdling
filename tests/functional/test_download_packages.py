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
