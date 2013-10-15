from __future__ import absolute_import, print_function, unicode_literals
from mock import Mock
from nose.tools import nottest
import os
import errno

from curdling import util
from curdling.exceptions import ReportableError
from curdling.index import Index
from curdling.install import Install
from curdling.database import Database

from curdling.services.base import Service
from curdling.services.downloader import Downloader, Finder
from curdling.services.curdler import Curdler
from curdling.services.installer import Installer

from . import FIXTURE


def test_downloader_with_no_sources():
    "It should be possible to download packages from pip repos with no sources"

    # Given the following downloader component with NO SOURCES
    finder = Finder()

    # When I try to retrieve a package from it, than I see it just blows up
    # with a nice exception
    finder.handle.when.called_with(
        'tests', {'requirement': 'gherkin==0.1.0'}).should.throw(
            ReportableError)


def test_downloader():
    "It should be possible to download packages from pip repos"

    # Given that I have a finder pointing to our local pypi server
    finder = Finder(**{
        'conf': {'pypi_urls': ['http://localhost:8000/simple']},
    })

    # And a downloader pointing to a temporary index
    index = Index(FIXTURE('tmpindex'))
    downloader = Downloader(**{'index': index})

    # When I find the link
    link = finder.handle('tests', {'requirement': 'gherkin (== 0.1.0)'})

    # And When I try to retrieve a package from it
    downloader.handle('main', link)

    # Then I see that the package was downloaded correctly to the storage
    index.get('gherkin==0.1.0').should_not.be.empty

    # And I cleanup the mess
    index.delete()


def test_finder_hyphen_on_pkg_name():
    "Finder#handle() should be able to locate packages with hyphens on the name"

    # Given a finder component
    finder = Finder(**{
        'conf': {'pypi_urls': ['http://localhost:8000/simple']},
    })

    # When I try to retrieve a package from it
    url = finder.handle('main', {'requirement': 'fake-pkg (0.0.0)'})

    # Then I see that the package was downloaded correctly to the storage
    url.should.equal({
        'requirement': 'fake-pkg (0.0.0)',
        'locator_url': 'http://localhost:8000/simple/',
        'url': 'http://localhost:8000/simple/fake-pkg/fake-pkg-0.0.0.tar.gz',
    })


def test_finder_underscore_on_pkg_name():
    "Finder#handle() should be able to locate packages with underscore on the name"

    # Given a finder component
    finder = Finder(**{
        'conf': {'pypi_urls': ['http://localhost:8000/simple']},
    })

    # When I try to retrieve a package from it
    url = finder.handle('main', {'requirement': 'fake_pkg (0.0.0)'})

    # Then I see that the package was downloaded correctly to the storage
    url.should.equal({
        'requirement': 'fake_pkg (0.0.0)',
        'locator_url': 'http://localhost:8000/simple/',
        'url': 'http://localhost:8000/simple/fake-pkg/fake-pkg-0.0.0.tar.gz',
    })


def test_finder_not_found():
    "Finder#handle() should raise `ReportableError` if it can't find the package"

    # Given a finder component
    finder = Finder(**{
        'conf': {'pypi_urls': ['http://localhost:8000/simple']},
    })

    # When I try to retrieve a package from it
    finder.handle.when.called_with(
        'main', {'requirement': 'donotexist==0.1.0'}).should.throw(ReportableError,
            'Requirement `donotexist==0.1.0\' not found')


def test_curd_package():
    "It should possible to convert regular packages to wheels"

    # Given that I have a storage containing a package
    index = Index(FIXTURE('storage1'))
    index.scan()

    # And a curdling using that index
    curdling = Curdler(**{'index': index})

    # When I request a curd to be created
    package = curdling.handle('main', {
        'tarball': index.get('gherkin==0.1.0;~whl'),
        'requirement': 'gherkin (0.1.0)',
    })

    # Then I see it's a wheel package.
    package['wheel'].should.match(
        FIXTURE('storage1/gherkin-0.1.0-py\d{2}-none-any.whl'))

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
    installer.handle('main', {
        'requirement': 'gherkin==0.1.0',
        'wheel': index.get('gherkin==0.1.0;whl'),
    })

    # Then I see that the package was installed
    Database.check_installed('gherkin==0.1.0').should.be.true

    # And I uninstall the package
    Database.uninstall('gherkin==0.1.0')



def test_retrieve_and_build():
    "Install#retrieve_and_build() "

    # Given that I have an installer with a working index
    index = Index(FIXTURE('tmp'))
    installer = Install(**{
        'conf': {
            'index': index,
            'pypi_urls': ['http://localhost:8000/simple']
        },
    })
    installer.pipeline()

    # And I feed the installer with a requirement
    installer.feed('tests', requirement='gherkin')

    # And start the installer
    installer.start()

    # When I run the retrieve and build loop
    packages = installer.retrieve_and_build()

    # Than I see that the package was retrieved
    packages.should.equal(set(['gherkin']))

    # And I clean the mess
    index.delete()
