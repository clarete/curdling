# Curdling - Concurrent package manager for Python
#
# Copyright (C) 2013-2014  Lincoln Clarete <lincoln@clarete.li>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import, print_function, unicode_literals
from curdling import freeze
from mock import patch, Mock


def test_find_imported_modules():
    "freeze.find_imported_modules() Should find all the imported modules in a string with Python code"

    # Given the following snippet
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

    # Given the following snippet
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


def test_find_imported_modules4():
    "freeze.find_imported_modules() Should filter the module path when it has more than one level"

    # Given the following snippet
    code = '''
from .relative import stuff
'''

    # When I query the imported modules
    names = freeze.find_imported_modules(code)

    # Then I see that the result names match the imported modules in
    # the code, skipping the local modules (.)
    names.should.equal([])


def test_find_imported_modules3():
    "freeze.find_imported_modules() Should skip any local imports (from . import x)"

    # Given the following snippet
    code = '''
from . import Image
import functools
'''

    # When I query the imported modules
    names = freeze.find_imported_modules(code)

    # Then I see that the result names match the imported modules in
    # the code, skipping the local modules (.)
    names.should.equal(['functools'])


@patch('curdling.freeze.imp')
@patch('curdling.freeze.sys')
def test_get_module_path(sys, imp):
    "freeze.get_module_path() Should return the file path of a module without importing it"

    sys.path = ['/u/l/p/site-packages']
    imp.find_module.return_value = ['', '/u/l/p/site-packages/sure']

    # Given a module name
    module = 'sure'

    # When I get its module path
    path = freeze.get_module_path(module)

    # Then I see that the file matches the expectations
    path.should.equal('sure')


@patch('curdling.freeze.imp')
@patch('curdling.freeze.sys')
def test_get_module_path2(sys, imp):
    "freeze.get_module_path() Should return the file path without the .py[cO] extension"

    sys.path = ['/u/l/p/site-packages']
    imp.find_module.return_value = ['', '/u/l/p/site-packages/mock.py']

    # Given a module name
    module = 'mock'

    # When I get its module path
    path = freeze.get_module_path(module)

    # Then I see that the file matches the expectations
    path.should.equal('mock')


@patch('curdling.freeze.DistributionPath')
def test_get_distribution_from_source_file(DistributionPath):
    "freeze.get_distribution_from_source_file(file_path) Should return the Distribution that contains `file_path`"

    # Given a path for a package
    path = 'sure/__init__.pyc'

    # When I retrieve the distribution for a given file
    distribution = freeze.get_distribution_from_source_file(path)

    # Then I see that the function tried to use the module name as the
    # package name.
    DistributionPath.return_value.get_distribution.assert_called_once_with(
        'sure',
    )


@patch('curdling.freeze.DistributionPath')
def test_get_distribution_from_source_file_file_path_being_a_directory(DistributionPath):
    "freeze.get_distribution_from_source_file(file_path) Should support receiving relative directories in `file_path`"

    # Given a path for a package
    path = 'sure'

    # When I retrieve the distribution for a given file
    distribution = freeze.get_distribution_from_source_file(path)

    # Then I see that the function tried to use the module name as the
    # package name.
    DistributionPath.return_value.get_distribution.assert_called_once_with(
        'sure',
    )


@patch('curdling.freeze.get_module_path', Mock())
@patch('curdling.freeze.get_distribution_from_source_file')
def test_get_requirements(get_distribution_from_source_file):
    "freeze.get_requirements() Should return a list of imports in a piece of code"

    # Given the following snippet
    code = '''
from distlib import util

print(util.in_venv())
'''

    # And a fake distribution
    distribution = Mock()
    distribution.name = 'distlib'
    distribution.version = '0.1.2'
    get_distribution_from_source_file.return_value = distribution

    # When I try to figure out which packages I need to run this
    # piece of code
    requirements = freeze.get_requirements(code)

    # Then I see it found the right version of 'distlib' our only
    # requirement here
    requirements.should.equal(['distlib==0.1.2'])
