from __future__ import absolute_import, unicode_literals, print_function
from mock import call, patch, Mock
from nose.tools import nottest

import io
import os
import errno

from curdling.install import Install
from curdling.index import Index, PackageNotFound
from curdling.util import expand_requirements, filehash
from curdling.services.base import Service
from curdling.signal import Signal, SignalEmitter


# -- curdling/util.py --


@patch('io.open')
def test_expand_requirements(open_func):
    "It should be possible to include other files inside"

    # Given that I have two files, called `development.txt` and
    # `requirements.txt` with the following content:
    open_func.return_value.read.side_effect = (
        '-r requirements.txt\nsure==0.2.1\n',  # development.txt
        'gherkin==0.1.0\n\n\n',                # requirements.txt
    )

    # When I expand the requirements
    requirements = expand_requirements('development.txt')

    # Then I see that all the required files were retrieved
    requirements.should.equal([
        'gherkin (== 0.1.0)',
        'sure (== 0.2.1)',
    ])


@patch('io.open')
def test_expand_commented_requirements(open_func):
    "expand_requirements() should skip commented lines"

    # Given that I have a file `development.txt` and with the following
    # content:
    open_func.return_value.read.return_value = (
        '# -r requirements.txt\n\n\n'   # comment
        'gherkin==0.1.0\n\n\n'          # requirements.txt
    )

    # When I expand the requirements
    requirements = expand_requirements('development.txt')

    # Then I see that all the required files were retrieved
    requirements.should.equal([
        'gherkin (== 0.1.0)',
    ])


@patch('io.open')
def test_expand_requirements_ignore_http_links(open_func):
    "It should be possible to parse files with http links"

    # Given that I have a file `development.txt` and with the following
    # content:
    open_func.return_value.read.return_value = (
        'sure==0.2.1\nhttp://python.org'
    )

    # When I expand the requirements
    requirements = expand_requirements('development.txt')

    # Then I see that all the required files were retrieved
    requirements.should.equal([
        'sure (== 0.2.1)',
    ])


def test_filehash():
    "filehash() should return the hash file objects"

    # Given that I have a file instance
    fp = io.StringIO('My Content')

    # When I call the filehash function
    hashed = filehash(fp, 'md5')

    # Then I see the hash was right
    hashed.should.equal('a86c5dea3ad44078a1f79f9cf2c6786d')


# -- curdling/install.py --


@patch('curdling.install.DistributionPath')
def test_check_installed(DistributionPath):
    "It should be possible to check if a certain package is currently installed"

    DistributionPath.return_value.get_distribution.return_value = Mock()
    Install({}).check_installed('gherkin==0.1.0').should.be.true

    DistributionPath.return_value.get_distribution.return_value = None
    Install({}).check_installed('gherkin==0.1.0').should.be.false


def test_request_install_no_cache():
    "Request the installation of a package when there is no cache"

    # Given that I have an environment
    index = Mock()
    index.get.side_effect = PackageNotFound('gherkin==0.1.0', 'whl')
    env = Install(conf={'index': index})
    env.start_services()
    env.check_installed = Mock(return_value=False)
    env.downloader = Mock()

    # When I request an installation of a package
    env.request_install('main', 'gherkin==0.1.0')

    # Then I see that the caches were checked
    env.check_installed.assert_called_once_with('gherkin==0.1.0')

    list(env.index.get.call_args_list).should.equal([
        call('gherkin==0.1.0;whl'),
        call('gherkin==0.1.0;~whl'),
    ])

    # And then I see that the download queue was populated
    env.downloader.queue.assert_called_once_with('main', 'gherkin==0.1.0')


def test_request_install_installed_package():
    "Request the installation of an already installed package"

    # Given that I have an environment
    index = Mock()
    env = Install(conf={'index': index})
    env.start_services()
    env.check_installed = Mock(return_value=True)
    env.downloader = Mock()

    # When I request an installation of a package
    env.request_install('main', 'gherkin==0.1.0').should.be.true

    # Then I see that, since the package was installed, the local cache was not
    # queried
    env.check_installed.assert_called_once_with('gherkin==0.1.0')
    env.index.get.called.should.be.false

    # And then I see that the download queue was not touched
    env.downloader.queue.called.should.be.false


def test_request_install_cached_package():
    "Request the installation of a cached package"

    # Given that I have a loaded local cache
    index = Index('')
    index.storage = {'gherkin': {'0.1.0': ['storage1/gherkin-0.1.0.tar.gz']}}

    # And that I have an environment associated with that local cache
    env = Install(conf={'index': index})
    env.start_services()
    env.check_installed = Mock(return_value=False)
    env.downloader = Mock()
    env.installer = Mock()
    env.curdler = Mock()

    # When I request an installation of a package
    env.request_install('main', 'gherkin==0.1.0')

    # Then I see that, since the package was not installed, the locall cache
    # was queried and returned the right entry
    env.check_installed.assert_called_once_with('gherkin==0.1.0')

    # And I see that the install queue was populated
    env.curdler.queue.assert_called_once_with(
        'main', 'gherkin==0.1.0', path='storage1/gherkin-0.1.0.tar.gz')

    # And that the download queue was not touched
    env.downloader.queue.called.should.be.false
    env.installer.queue.called.should.be.false


@nottest
def test_request_install_cached_wheels():
    "Request the installation of a cached package"

    # Given that I have a loaded local cache
    index = Index('')
    index.storage = {'gherkin': {'0.1.0': ['storage1/gherkin-0.1.0-py27-none-any.whl']}}

    # And that I have an environment associated with that local cache
    env = Install(conf={'index': index})
    env.check_installed = Mock(return_value=False)
    env.services['download'] = Mock()
    env.services['install'] = Mock()

    # When I request an installation of a package
    env.request_install('gherkin==0.1.0').should.be.false

    # Then I see that, since the package was not installed, the locall cache
    # was queried and returned the right entry
    env.check_installed.assert_called_once_with('gherkin==0.1.0')

    # And I see that the install queue was populated
    env.services['install'].queue.assert_called_once_with(
        'gherkin==0.1.0', 'main', path='storage1/gherkin-0.1.0-py27-none-any.whl')

    # And that the download queue was not touched
    env.services['download'].queue.called.should.be.false


# -- Index --


@patch('curdling.index.os')
def test_index_ensure_path(patched_os):
    "Test utility method Index.ensure_path()"

    # We'll need that inside of ensure_path()
    patched_os.path.dirname = os.path.dirname

    # Given that I have an index
    index = Index('')

    # When I call ensure_path(resource) against a directory that doesn't seem
    # to exist, it should try to create the directory for the resource
    patched_os.path.isdir.return_value = False
    index.ensure_path('path/to/my/resource')
    patched_os.makedirs.assert_called_once_with('path/to/my')


@patch('curdling.index.os')
def test_index_ensure_path_for_existing_dirs(patched_os):
    "Test utility method Index.ensure_path() for existing directories"

    # We'll need that inside of ensure_path()
    patched_os.path.dirname = os.path.dirname

    # Given that I have an index
    index = Index('')

    # When I call ensure_path(resource) against a directory that exists to
    # exists, it *SHOULD NOT* try to create the directory
    patched_os.path.isdir.return_value = True
    index.ensure_path('path/to/my/resource')
    patched_os.makedirs.called.should.be.false


def test_index_feed_backend():
    "It should be possible to save package paths granularly"

    # Given the following index
    index = Index('')

    # When I index a couple files
    index.index('http://localhost:800/p/gherkin-0.1.0-py27-none-any.whl')
    index.index('gherkin-0.1.0.tar.gz')
    index.index('Gherkin-0.1.5.tar.gz')  # I know, weird right?
    index.index('a/weird/dir/gherkin-0.2.0.tar.gz')

    # Then I see that the backend structure looks right
    dict(index.storage).should.equal({
        'gherkin': {
            '0.2.0': [
                'gherkin-0.2.0.tar.gz',
            ],
            '0.1.5': [
                'Gherkin-0.1.5.tar.gz',
            ],
            '0.1.0': [
                'gherkin-0.1.0-py27-none-any.whl',
                'gherkin-0.1.0.tar.gz',
            ],
        },
    })


def test_index_get():
    "It should be possible to search for packages using different criterias"

    # Given that I have an index loaded with a couple package references
    index = Index('')
    index.storage = {
        'gherkin': {
            '0.2.0': [
                'gherkin-0.2.0.tar.gz',
            ],
            '0.1.5': [
                'gherkin-0.2.0.tar.gz',
            ],
            '0.1.1': [
                'gherkin-0.1.1.tar.gz',
            ],
            '0.1.0': [
                'gherkin-0.1.0.tar.gz',
                'gherkin-0.1.0-py27-none-any.whl',
            ],
        }
    }

    # Let's do some random assertions

    # No version: Always brings the newest
    index.get('gherkin').should.equal('gherkin-0.2.0.tar.gz')

    # With a range of versions: Always brings the newest
    index.get('gherkin (> 0.1.0)').should.equal('gherkin-0.2.0.tar.gz')

    # With a handful of version specs: Find the matching version and prefer whl
    index.get('gherkin (>= 0.1.0, < 0.1.5, != 0.1.1)').should.equal('gherkin-0.1.0-py27-none-any.whl')

    # With version: Always prefers the wheel
    index.get('gherkin (== 0.1.0, <= 0.2.0)').should.equal('gherkin-0.1.0-py27-none-any.whl')

    # With version and format: Prefers anything but `whl'
    index.get('gherkin (== 0.1.0);~whl').should.equal('gherkin-0.1.0.tar.gz')

    # With version range and no format: Finds the highest version with the :)
    index.get.when.called_with('gherkin (== 0.1.1);whl').should.throw(
        PackageNotFound, (
            "The index does not have the requested package: "
            "gherkin (== 0.1.1) (whl)"))

    # With version and a format that is not available: Blows up! :)
    index.get.when.called_with('gherkin (== 0.1.1);whl').should.throw(
        PackageNotFound, (
            "The index does not have the requested package: "
            "gherkin (== 0.1.1) (whl)"))

    # With a version we simply don't have: Blows up! :)
    index.get.when.called_with('gherkin (== 0.2.1)').should.throw(
        PackageNotFound, (
            "The index does not have the requested package: "
            "gherkin (== 0.2.1)"))

    # With a package we simply don't have: Blows up! :)
    index.get.when.called_with('nonexisting (== 0.2.1)').should.throw(
        PackageNotFound, (
            "The index does not have the requested package: "
            "nonexisting (== 0.2.1)"))

    # Case insensitive
    index.get('Gherkin').should.equal('gherkin-0.2.0.tar.gz')



def test_index_get_corner_case_pkg_name():
    "It should be possible to search for packages that contain `_` in their name"

    # Given that I have an index loaded with a couple package references
    index = Index('')
    index.storage = {
        'python-gherkin': {
            '0.1.0': [
                'python_gherkin-0.1.0.tar.gz',
            ]
        }
     }


    index.get('python-gherkin==0.1.0;~whl').should.equal('python_gherkin-0.1.0.tar.gz')


# -- Signals --


def test_signal():
    "It should possible to emit signals"

    # Given that I have a button that emits signals
    class Button(SignalEmitter):
        clicked = Signal()

    # And a content to store results of the callback function associated with
    # the `clicked` signal in the next lines
    callback = Mock()

    # And an instance of that button class
    b = Button()
    b.connect('clicked', callback)

    # When button instance gets clicked (IOW: when we emit the `clicked`
    # signal)
    b.emit('clicked', a=1, b=2)

    # Then we see that the  dictionary was populated as expected
    callback.assert_called_once_with(a=1, b=2)


def test_signal_that_does_not_exist():
    "AttributeError must be raised if a given signal does not exist"

    # Given that I have a button that emits signals, but with no signals
    class Button(SignalEmitter):
        pass

    # And an instance of that button class
    b = Button()

    # When I try to connect an unknown signal to the instance, Then I see
    # things just explode with a nice message.
    b.connect.when.called_with('clicked', lambda *a: a).should.throw(
        AttributeError,
        'There is no such signal (clicked) in this emitter (button)',
    )
