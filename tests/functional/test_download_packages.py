from curdling.download import PipSource, DownloadManager, MemoryStorage


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
