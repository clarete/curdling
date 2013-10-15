from __future__ import absolute_import, print_function, unicode_literals
from mock import call, patch, Mock
from nose.tools import nottest

from curdling.index import Index, PackageNotFound
from curdling.install import Install
from curdling import install
from curdling.maestro import Maestro


def test_decorator_only():
    "install@only() should not call the decorated function if `field` is set"

    callback = Mock(__name__=b'callback')
    decorated = install.only(callback, 'tarball')

    decorated('tests', tarball='tarball.tar.gz')
    callback.assert_called_once_with(
        'tests', tarball='tarball.tar.gz')

    callback2 = Mock(__name__=b'callback')
    decorated = install.only(callback, 'tarball')

    decorated('tests', directory='/path/to/a/package')
    callback2.called.should.be.false


def test_decorator_mark():
    "install@mark() should use the maestro API to update the requirement status and data"

    maestro = Maestro()
    maestro.file_requirement('curd')

    install.mark(maestro, Maestro.Status.RETRIEVED)(
        'tests', requirement='curd', tarball='curd.tar.gz')
    (maestro.get_status('curd') & Maestro.Status.RETRIEVED).should.be.true
    maestro.get_data('curd', 'tarball').should.equal('curd.tar.gz')

    install.mark(maestro, Maestro.Status.BUILT)(
        'tests', requirement='curd', wheel='curd.whl')
    (maestro.get_status('curd') & Maestro.Status.RETRIEVED).should.be.true
    (maestro.get_status('curd') & Maestro.Status.BUILT).should.be.true
    maestro.get_data('curd', 'wheel').should.equal('curd.whl')


# def test_request_install_no_cache():
#     "Request the installation of a package when there is no cache"

#     # Given that I have an environment
#     index = Mock()
#     index.get.side_effect = PackageNotFound('gherkin==0.1.0', 'whl')
#     env = Install(conf={'index': index})
#     env.start_services()
#     env.database.check_installed = Mock(return_value=False)
#     env.finder = Mock()

#     # When I request an installation of a package
#     env.request_install('main', requirement='gherkin==0.1.0')

#     # Then I see that the caches were checked
#     env.database.check_installed.assert_called_once_with('gherkin==0.1.0')

#     list(env.index.get.call_args_list).should.equal([
#         call('gherkin==0.1.0;whl'),
#         call('gherkin==0.1.0;~whl'),
#     ])

#     # And then I see that the download queue was populated
#     env.finder.queue.assert_called_once_with('main', requirement='gherkin==0.1.0')


# @nottest
# def test_request_install_installed_package():
#     "Request the installation of an already installed package"

#     # Given that I have an environment
#     index = Mock()
#     env = Install(conf={'index': index})
#     env.start_services()
#     env.database.check_installed = Mock(return_value=True)
#     env.downloader = Mock()

#     # When I request an installation of a package
#     env.request_install('main', requirement='gherkin==0.1.0').should.be.true

#     # Then I see that, since the package was installed, the local cache was not
#     # queried
#     env.database.check_installed.assert_called_once_with('gherkin==0.1.0')
#     env.index.get.called.should.be.false

#     # And then I see that the download queue was not touched
#     env.downloader.queue.called.should.be.false


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


def test_pipeline_link_download():
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


def test_pipeline_finder_found_downloader():
    "Install#pipelien() should route the finder output to the downloader"

    # Given that I have the install command
    index = Index('')
    index.storage = {}
    install = Install(conf={'index': index})

    # And I mock the downloader service end-point
    install.finder.queue = Mock()
    install.downloader.queue = Mock()
    install.pipeline()

    # Feed the installer with the requirement
    install.finder.queue = Mock()
    install.feed('tests', requirement='package')

    # When I fire the finder.finished() signal with proper data
    install.finder.emit('finished',
        'finder',
        requirement='package',
        url='http://srv.com/package.tar.gz',
        locator_url='http://usr:passwd@srv.com/simple',
    )

    # Then I see that the downloader received a request
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
    install.curdler.queue = Mock(__name__=b'queue')
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
    install.dependencer.queue = Mock(__name__=b'queue')
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
    install.dependencer.queue = Mock(__name__=b'queue')
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
    install.feed = Mock(__name__=b'feed')
    install.pipeline()

    # When I fire the download.finished() signal with proper data
    install.dependencer.emit('dependency_found', 'dependencer', requirement='curdling (0.3.0)')

    # Than I see that the curdler received a request
    install.feed.assert_called_once_with(
        'dependencer', requirement='curdling (0.3.0)')


def test_count_errors():
    "Install#errors Should contain all the errors happened in all the services"

    # Given that I have the install command
    index = Index('')
    index.storage = {}
    install = Install(conf={'index': index})
    install.pipeline()

    install.finder.handle = Mock(side_effect=Exception('P0wned!'))

    # When I feed the installer with a requirement
    install.feed('tests', requirement='pkg')
    install.finder.queue(None)
    install.finder._worker()

    install.errors.should.have.length_of(1)
    str(install.errors[0]['exception']).should.equal('P0wned!')


def test_count():
    "Install#count() Should know how many finished requests a given service has"

    # Given that I have the install command
    index = Index('')
    index.storage = {}
    install = Install(conf={'index': index})
    install.pipeline()

    install.finder.handle = Mock(return_value={'requirement': 'pkg'})

    # When I feed the installer with a requirement
    install.feed('tests', requirement='pkg')
    install.finder.queue(None)
    install.finder._worker()

    install.count('finder').should.equal(1)
