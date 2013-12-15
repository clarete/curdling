from curdling import freeze


def test_find_imported_modules():
    "freeze.find_imported_modules() Should find all the imported modules in a string with Python code"

    # Given the following snipet
    code = '''
import curdling

def blah(): pass

import math

print(curdling)
'''

    # When I query the imported modules
    names = freeze.find_imported_modules(code)

    # Then I see that the result names match the imported modules in
    # the code
    names.should.equal(['curdling', 'math'])


def test_find_imported_modules2():
    "freeze.find_imported_modules() Should also find imports declared with 'from x import y' syntax"

    # Given the following snipet
    code = '''
from PIL import Image

def blah(): pass

import functools

print(curdling)
'''

    # When I query the imported modules
    names = freeze.find_imported_modules(code)

    # Then I see that the result names match the imported modules in
    # the code
    names.should.equal(['PIL', 'functools'])


def test_find_imported_modules3():
    "freeze.find_imported_modules() Should skip any local imports (from . import x)"

    # Given the following snipet
    code = '''
from . import Image
import functools
'''

    # When I query the imported modules
    names = freeze.find_imported_modules(code)

    # Then I see that the result names match the imported modules in
    # the code, skipping the local modules (.)
    names.should.equal(['functools'])


def test_get_module_path():
    "freeze.get_module_path() Should return the file path of a module without importing it"

    # Given a module name
    module = 'curdling'

    # When I get its module path
    path = freeze.get_module_path(module)

    # Then I see that the file matches the expectations
    path.endswith('curdling/curdling').should.be.true


def test_get_distribution_from_source_file():
    "freeze.get_distribution_from_source_file(file_path) Should return the Distribution that contains `file_path`"

    # Given a path for a package
    path = 'curdling/curdling'

    # When I retrieve the distribution for a given file
    distribution = freeze.get_distribution_from_source_file(path)
