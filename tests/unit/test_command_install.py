from __future__ import absolute_import, print_function, unicode_literals
from mock import call, patch, Mock
from nose.tools import nottest

from curdling.exceptions import VersionConflict, ReportableError
from curdling.index import Index, PackageNotFound
from curdling.install import Install
from curdling import install


def test_decorator_only():
    "install@only() should not call the decorated function if `field` is set"

    callback = Mock(__name__=str('callback'))
    decorated = install.only(callback, 'tarball')

    decorated('tests', tarball='tarball.tar.gz')
    callback.assert_called_once_with(
        'tests', tarball='tarball.tar.gz')

    callback2 = Mock(__name__=str('callback2'))
    decorated = install.only(callback2, 'tarball')

    decorated('tests', directory='/path/to/a/package')
    callback2.called.should.be.false


def test_install_feed_when_theres_a_tarball_cached():
    "Install#feed() Should route the requirements that already have a tarball to the curdler"

    # Given that I have a loaded local cache
    index = Index('')
    index.storage = {'gherkin': {'0.1.0': ['storage1/gherkin-0.1.0.tar.gz']}}

    # And that I have an environment associated with that local cache
    env = Install(conf={'index': index})
    env.pipeline()
    env.downloader.queue = Mock()
    env.installer.queue = Mock()
    env.curdler.queue = Mock()

    # When I request an installation of a package
    env.feed('main', requirement='gherkin==0.1.0')

    # # Then I see that, since the package was not installed, the locall cache
    # # was queried and returned the right entry
    # env.database.check_installed.assert_called_once_with('gherkin==0.1.0')

    # And I see that the install queue was populated
    env.curdler.queue.assert_called_once_with(
        'main',
        requirement='gherkin==0.1.0',
        tarball='storage1/gherkin-0.1.0.tar.gz')

    # And that the download queue was not touched
    env.downloader.queue.called.should.be.false
    env.installer.queue.called.should.be.false


def test_install_feed_when_theres_a_wheel_cached():
    "Install#feed() Should route the requirements that already have a wheel to the dependencer"

    # Given that I have a loaded local cache
    index = Index('')
    index.storage = {'gherkin': {'0.1.0': ['storage1/gherkin-0.1.0-py27-none-any.whl']}}

    # And that I have an environment associated with that local cache
    env = Install(conf={'index': index})
    env.pipeline()
    env.downloader.queue = Mock()
    env.dependencer.queue = Mock()
    env.curdler.queue = Mock()

    # When I request an installation of a package
    env.feed('tests', requirement='gherkin==0.1.0')

    # # Then I see that, since the package was not installed, the locall cache
    # # was queried and returned the right entry
    # env.check_installed.assert_called_once_with('gherkin==0.1.0')

    # And I see that the install queue was populated
    env.dependencer.queue.assert_called_once_with(
        'tests',
        requirement='gherkin==0.1.0',
        wheel='storage1/gherkin-0.1.0-py27-none-any.whl',
    )

    # And that the download queue was not touched
    env.downloader.queue.called.should.be.false


def test_feed_requirement_finder():
    "Install#feed() should route all queued requirements to the finder"

    # Given that I have the install command
    index = Index('')
    index.storage = {}
    install = Install(conf={'index': index})
    install.pipeline()

    # And I mock some service end-points
    install.finder.queue = Mock()

    # When I request the installation of a new requirement
    install.feed('tests', requirement='curdling')

    # Then I see the finder received a request
    install.finder.queue.assert_called_once_with(
        'tests', requirement='curdling')


def test_feed_link_download():
    "Install#feed() should route all queued links to the downloader"

    # Given that I have the install command
    index = Index('')
    index.storage = {}
    install = Install(conf={'index': index})
    install.pipeline()

    # And I mock some service end-points
    install.downloader.queue = Mock()

    # When I request the installation of a new requirement
    install.feed('tests', requirement='http://srv/pkgs/curdling-0.1.tar.gz')

    # I see that the downloader received a request
    install.downloader.queue.assert_called_once_with(
        'tests',
        requirement='http://srv/pkgs/curdling-0.1.tar.gz',
        url='http://srv/pkgs/curdling-0.1.tar.gz')


def test_feed_filter_dups():
    "Install#feed() Should skip duplicated requirements"

    # Given that I have the install command
    index = Index('')
    index.storage = {}
    install = Install(conf={'index': index})

    # And I mock the finder service end-point
    install.finder.queue = Mock()
    install.pipeline()

    # Feed the installer with the requirement
    install.feed('tests', requirement='package')
    install.finder.queue.assert_called_once_with('tests', requirement='package')
    install.mapping.requirements.should.equal(set(['package']))

    # When I fire the finder.finished() signal with proper data
    install.feed('tests', requirement='package')

    # Then I see the feed function just skipped this repeated requirement
    install.finder.queue.assert_called_once_with('tests', requirement='package')
    install.mapping.requirements.should.equal(set(['package']))


def test_feed_filter_blacklisted_packages():
    "Install#feed() Should skip blacklisted package names"

    # Given that I have the install command
    index = Index('')
    index.storage = {}
    install = Install(conf={'index': index})

    # And I mock the finder service end-point
    install.finder.queue = Mock()
    install.pipeline()

    # When I feed the installer with the requirement
    install.feed('tests', requirement='setuptools')

    # Then I see it was just skipped
    install.finder.queue.called.should.be.false


def test_pipeline_update_mapping_stats():
    "Install#pipeline() Should update the Install#mapping#stats"

    # Given that I have the install command
    index = Index('')
    index.storage = {}
    install = Install(conf={'index': index})
    install.pipeline()

    install.finder.handle = Mock(return_value={
        'requirement': 'pkg',
        'url': 'pkg.tar.gz',
    })

    # When I feed the installer with a requirement
    install.feed('tests', requirement='pkg')
    install.finder.queue(None)
    install.finder._worker()

    install.mapping.count('finder').should.equal(1)


def test_pipeline_update_mapping_errors():
    "Install#pipeline() Should update Install#mapping#errors whenever an error occurs"

    # Given that I have the install command
    index = Index('')
    index.storage = {}
    install = Install(conf={'index': index})
    install.pipeline()

    install.finder.handle = Mock(side_effect=Exception('P0wned!'))

    # When I feed the installer with a requirement
    install.feed('tests', requirement='pkg (0.1)')
    install.finder.queue(None)
    install.finder._worker()

    install.mapping.errors.should.have.length_of(1)
    str(install.mapping.errors['pkg'][0]['exception']).should.equal('P0wned!')


def test_pipeline_update_mapping_wheels():
    "Install#pipeline() Should update the list Install#mapping#wheels every time we process a dependency"

    # Given that I have the install command
    install = Install(conf={})
    install.pipeline()

    # When the dependencer runs
    install.dependencer.emit(
        'finished',             # signal name
        'tests',                # requester
        requirement='pkg (0.1)',
        wheel='pkg.whl')

    # Than I see that the `Install.mapping.wheels` property was updated
    # properly
    install.mapping.wheels.should.equal({
        'pkg (0.1)': 'pkg.whl',
    })


def test_pipeline_finder_found_downloader():
    "Install#pipeline() should route the finder output to the downloader"

    # Given that I have the install command
    index = Index('')
    index.storage = {}
    install = Install(conf={'index': index})

    # And I mock the downloader service end-point
    install.finder.queue = Mock(__name__=str('queue'))
    install.downloader.queue = Mock(__name__=str('queue'))
    install.pipeline()

    # Feed the installer with the requirement
    install.finder.queue = Mock()
    install.feed('tests', requirement='package')
    install.feed('tests', requirement='package (0.0.1)')

    # When I fire the finder.finished() signal with proper data
    install.finder.emit('finished',
        'finder',
        requirement='package',
        url='http://srv.com/package.tar.gz',
        locator_url='http://usr:passwd@srv.com/simple',
    )

    # And manually add the first package to the `processing_packages` set,
    # because we mock `queue`, the component that actually does that for us.
    install.downloader.processing_packages.add('package.tar.gz')

    # And When I fire another finished signal with a different requirement but
    # the same url
    install.finder.emit('finished',
        'finder',
        requirement='package (0.0.1)',
        url='http://another.srv.com/package.tar.gz',
        locator_url='http://srv.com/simple',
    )

    # Then I see that the downloader received a single request. The second one
    # was duplicated
    install.downloader.queue.assert_called_once_with(
        'finder',
        requirement='package',
        url='http://srv.com/package.tar.gz',
        locator_url='http://usr:passwd@srv.com/simple',
    )


def test_pipeline_downloader_tarzip_curdler():
    "Install#pipeline() should route all the tar/zip files to the curdler"

    # Given that I have the install command
    index = Index('')
    index.storage = {}
    install = Install(conf={'index': index})

    # And I mock the curdler service end-point and start all the services
    install.curdler.queue = Mock(__name__=str('queue'))
    install.pipeline()

    # Feed the installer with the requirement
    install.finder.queue = Mock()
    install.feed('tests', requirement='curdling')

    # When I fire the download.finished() signal with proper data
    install.downloader.emit('finished',
        'downloader',
        requirement='curdling',
        tarball='curdling-0.1.tar.gz')

    # Than I see that the curdler received a request
    install.curdler.queue.assert_called_once_with(
        'downloader',
        requirement='curdling',
        tarball='curdling-0.1.tar.gz')


def test_pipeline_downloader_wheel_dependencer():
    "Install#pipeline() should route all the wheel files to the dependencer"

    # Given that I have the install command
    index = Index('')
    index.storage = {}
    install = Install(conf={'index': index})

    # And I mock the curdler service end-point and start all the services
    install.dependencer.queue = Mock(__name__=str('queue'))
    install.pipeline()

    # Feed the installer with the requirement
    install.finder.queue = Mock()
    install.feed('tests', requirement='curdling')

    # When I fire the download.finished() signal with proper data
    install.downloader.emit('finished',
        'downloader',
        requirement='curdling',
        wheel='curdling-0.1.0-py27-none-any.whl')

    # Than I see that the curdler received a request
    install.dependencer.queue.assert_called_once_with(
        'downloader',
        requirement='curdling',
        wheel='curdling-0.1.0-py27-none-any.whl')


def test_pipeline_curdler_wheel_dependencer():
    "Install#pipeline() should route all the wheel files from the curdler to the dependencer"

    # Given that I have the install command
    index = Index('')
    index.storage = {}
    install = Install(conf={'index': index})

    # And I mock the curdler service end-point and start all the services
    install.dependencer.queue = Mock(__name__=str('queue'))
    install.pipeline()

    # Feed the installer with the requirement
    install.finder.queue = Mock()
    install.feed('tests', requirement='curdling')

    # When I fire the curdler.finished() signal with proper data
    install.curdler.emit('finished',
        'curdler',
        requirement='curdling',
        wheel='curdling-0.1.0-py27-none-any.whl')

    # Than I see that the dependencer received a request
    install.dependencer.queue.assert_called_once_with(
        'curdler',
        requirement='curdling',
        wheel='curdling-0.1.0-py27-none-any.whl')


def test_pipeline_dependencer_queue():
    "Install#pipeline() should route all the requirements from the dependencer to Install#feed()"

    # Given that I have the install command
    index = Index('')
    index.storage = {}
    install = Install(conf={'index': index})

    # And I mock the curdler service end-point and start all the services
    install.feed = Mock(__name__=str('feed'))
    install.pipeline()

    # When I fire the download.finished() signal with proper data
    install.dependencer.emit('dependency_found', 'dependencer', requirement='curdling (0.3.0)')

    # Than I see that the curdler received a request
    install.feed.assert_called_once_with(
        'dependencer', requirement='curdling (0.3.0)')



def test_load_installer():
    "Install#load_installer() should load all the wheels collected in Install#wheels and add them to the installer queue"

    # Given that I have the install command
    install = Install(conf={})
    install.pipeline()

    # And I mock the installer queue
    install.installer.queue = Mock(__name__=str('queue'))

    # And a few packages inside of the `Install.wheels` attribute
    install.mapping.wheels = {
        'package (0.1)': 'package-0.1-py27-none-any.whl',
        'another-package (0.1)': 'another_package-0.1-py27-none-any.whl',
    }

    # When I load the installer
    names, errors = install.load_installer()

    # Then I see no errors
    errors.should.be.empty

    # And Then I see the list of all successfully processed packages
    names.should.equal(set(['package', 'another-package']))

    # And Then I see that the installer should be loaded will all the
    # requested packages; This nasty `sorted` call is here to make it
    # work on python3. The order of the call list I build manually to
    # compare doesn't match the order of `call_args_list` from our
    # mock on py3 :/
    sorted(install.installer.queue.call_args_list, key=lambda i: i[1]['wheel']).should.equal([
        call('main',
             wheel='another_package-0.1-py27-none-any.whl',
             requirement='another-package (0.1)'),
        call('main',
             wheel='package-0.1-py27-none-any.whl',
             requirement='package (0.1)'),
    ])


def test_load_installer_handle_version_conflicts():
    "Install#load_installer() should return conflicts in all requirements being installed"

    # Given that I have the install command
    install = Install(conf={})
    install.pipeline()

    # And I mock the installer queue
    install.installer.queue = Mock(__name__=str('queue'))

    # And two conflicting packages requested
    install.mapping.wheels = {
        'package (0.1)': 'package-0.1-py27-none-any.whl',
        'package (0.2)': 'package-0.2-py27-none-any.whl',
    }

    # And I know it is a corner case for non-primary packages
    install.mapping.dependencies = {
        'package (0.1)': ['blah'],
        'package (0.2)': ['bleh'],
    }

    # When I load the installer
    names, errors = install.load_installer()

    # Then I see the list of all successfully processed packages
    names.should.equal(set(['package']))

    # And Then I see that the error list was filled properly
    errors.should.have.length_of(1)
    errors.should.have.key('package').with_value.being.a(list)
    errors['package'].sort(key=lambda i: i['requirement'], reverse=True)
    errors['package'].should.have.length_of(2)

    errors['package'][0]['dependency_of'].should.equal(['bleh'])
    errors['package'][0]['exception'].should.be.a(VersionConflict)
    str(errors['package'][0]['exception']).should.equal(
        'Requirement: package (0.2, 0.1), Available versions: 0.2, 0.1')

    errors['package'][1]['dependency_of'].should.equal(['blah'])
    errors['package'][1]['exception'].should.be.a(VersionConflict)
    str(errors['package'][1]['exception']).should.equal(
        'Requirement: package (0.2, 0.1), Available versions: 0.2, 0.1')


def test_load_installer_forward_errors():
    "Install#load_installer() Should forward errors from other services when `installable_packages` != `initial_requirements`"

    # Given that I have the install command with an empty index
    index = Index('')
    index.storage = {}
    install = Install(conf={'index': index})
    install.pipeline()

    # And I feed the installer with a requirement
    install.feed('tests', requirement='package')

    # And I cause an error in the download worker
    install.downloader.handle = Mock(side_effect=Exception('Beep-Bop'))

    # And I mock the installer queue
    install.installer.queue = Mock(__name__=str('queue'))

    # When I try to retrieve and build all the requirements
    install.start()
    install.retrieve_and_build()

    # And When I load the installer
    names, errors = install.load_installer()

    # Then I see the list of all successfully processed packages
    names.should.be.empty

    # And Then I see that the error list was filled properly
    errors.should.have.length_of(1)
    errors.should.have.key('package').with_value.being.a(list)
    errors['package'].should.have.length_of(1)

    errors['package'][0]['dependency_of'].should.equal([None])
    errors['package'][0]['exception'].should.be.a(ReportableError)
    str(errors['package'][0]['exception']).should.equal(
        'Requirement `package\' not found')
