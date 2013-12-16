from curdling import freeze
from . import FIXTURE


def test_get_module_path():
    "freeze.get_module_path() Should return the file path of a module without importing it"

    # Given a module name
    module = 'sure'

    # When I get its module path
    path = freeze.get_module_path(module)

    # Then I see that the file matches the expectations
    path.should.equal('sure')


def test_get_distribution_from_source_file():
    "freeze.get_distribution_from_source_file(file_path) Should return the Distribution that contains `file_path`"

    # Given a path for a package
    path = 'sure/__init__.pyc'

    # When I retrieve the distribution for a given file
    distribution = freeze.get_distribution_from_source_file(path)

    # Then I see the right distribution was found
    distribution.name.should.equal('sure')


def test_get_distribution_from_source_file_file_path_being_a_directory():
    "freeze.get_distribution_from_source_file(file_path) Should support receiving relative directories in `file_path`"

    # Given a path for a package
    path = 'sure'

    # When I retrieve the distribution for a given file
    distribution = freeze.get_distribution_from_source_file(path)

    # Then I see the right distribution was found
    distribution.name.should.equal('sure')


def test_get_requirements():
    "freeze.get_requirements() Should return a list of imports in a piece of code"

    # Given the following snippet
    code = '''
from distlib import util

print(util.in_venv())
'''

    # When I try to figure out which packages I need to run this
    # piece of code
    requirements = freeze.get_requirements(code)

    # Then I see it found the right version of 'distlib' our only
    # requirement here
    requirements.should.equal(['distlib==0.1.2'])  # Guaranteed in our requirements.txt


def test_get_requirements():
    "freeze.get_requirements() Should return a list of imports in a piece of code"

    # Given the following snippet
    code = '''
from mock import Mock

print(Mock())
'''

    # When I try to figure out which packages I need to run this
    # piece of code
    requirements = freeze.get_requirements(code)

    # Then I see it found the right version of 'distlib' our only
    # requirement here
    requirements.should.equal(['mock==1.0.1'])  # Guaranteed in our requirements.txt


def test_find_python_files():
    "freeze.find_python_files(path) Should find all the python files under `path`"

    # Given the following directory
    codebase = FIXTURE('codebase1')

    # When I list all the available python files
    python_files = freeze.find_python_files(codebase)

    # Then I see the list with all the files present in that given
    # directory
    python_files.should.equal([
        'codebase1/__init__.py',
        'codebase1/hello.py',
    ])
