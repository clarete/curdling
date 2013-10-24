from __future__ import absolute_import, print_function, unicode_literals
from mock import patch
from curdling.index import Index, PackageNotFound
import os


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
    index.index('package.name-0.1.0.tar.gz')

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
        'package.name': {
            '0.1.0': [
                'package.name-0.1.0.tar.gz',
            ]
        }
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
            "gherkin (0.1.1) (whl)"))

    # With version and a format that is not available: Blows up! :)
    index.get.when.called_with('gherkin (== 0.1.1);whl').should.throw(
        PackageNotFound, (
            "The index does not have the requested package: "
            "gherkin (0.1.1) (whl)"))

    # With a version we simply don't have: Blows up! :)
    index.get.when.called_with('gherkin (== 0.2.1)').should.throw(
        PackageNotFound, (
            "The index does not have the requested package: "
            "gherkin (0.2.1)"))

    # With a package we simply don't have: Blows up! :)
    index.get.when.called_with('nonexisting (== 0.2.1)').should.throw(
        PackageNotFound, (
            "The index does not have the requested package: "
            "nonexisting (0.2.1)"))

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
