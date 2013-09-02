from __future__ import absolute_import, unicode_literals, print_function
from curdling.index import Index

from . import FIXTURE



def test_index_from_file():
    "It should be possible to index packages from files"

    # Given the following index
    index = Index(FIXTURE('index'))

    # When I index a file
    index.from_file(FIXTURE('storage1/gherkin-0.1.0.tar.gz'))

    # Then I see it inside of the index
    index.find('gherkin==0.1.0', only=('gz',)).should.equal([
        FIXTURE('index/gherkin-0.1.0.tar.gz'),
    ])

    # And that there's no wheel available yet
    index.find('gherkin==0.1.0', only=('whl',))

    # And I clean the mess
    index.delete()


def test_index_from_data():
    "It should be possible to index data from memory"

    # Given the following index
    index = Index(FIXTURE('index'))

    # When I index a file
    data = open(FIXTURE('storage1/gherkin-0.1.0.tar.gz'), 'rb').read()
    index.from_data(package='gherkin==0.1.0', ext='gz', data=data)

    # Then I see it inside of the index
    index.find('gherkin==0.1.0').should.equal([
        FIXTURE('index/gherkin-0.1.0.tar.gz'),
    ])

    # And I clean the mess
    index.delete()


def test_index_scan():
    "It should be possible to scan for already existing folders"

    # Given that I have an index that points to a folder that already contains
    # packages
    index = Index(FIXTURE('storage1'))

    # When I scan the directory
    index.scan()

    # Then I can look for packages
    index.find('gherkin==0.1.0').should.equal([
        FIXTURE('storage1/gherkin-0.1.0.tar.gz'),
    ])
