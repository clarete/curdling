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

import ast
import imp
import os
import sys
from distlib.database import DistributionPath
from .util import logger


class ImportVisitor(ast.NodeVisitor):

    def __init__(self):
        self.imports = []

    def visit_Import(self, node):
        self.imports.append(node.names[0].name)

    def visit_ImportFrom(self, node):
        if node.level == 0:
            self.imports.append(node.module)


def find_imported_modules(code):
    visitor = ImportVisitor()
    visitor.visit(ast.parse(code))
    return visitor.imports


def get_module_path(module_name):
    module_path = imp.find_module(module_name)[1]
    possible_paths = ['']       # Avoid failure in max() if there's no
                                # prefix at all
    possible_paths.extend(path
        for path in sys.path
        if path in module_path)
    return os.path.splitext(module_path.replace(
        '{0}/'.format(max(possible_paths)), ''))[0]


def get_distribution_from_source_file(file_name):
    path = DistributionPath(include_egg=True)
    distribution = path.get_distribution(
        os.path.dirname(file_name) or file_name)
    return distribution


def get_requirements(code):
    requirements = []

    for module_name in find_imported_modules(code):
        print('module found: {0}'.format(module_name))
        path = get_module_path(module_name)

        # If we do have a module that matches tha name we still need
        # to know if it was installed as a package. If it was not, we
        # consider that the user is not interested in adding this
        # package to the requirements list, so we just skip it.
        distribution = get_distribution_from_source_file(path)
        if not distribution:
            continue

        # Let's build the output in a format that everybody
        # understands
        requirements.append('{0}=={1}'.format(
            distribution.name,
            distribution.version))

    return requirements


def find_python_files(path):
    source_files = []
    for root, directories, files in os.walk(path):
        for file_name in files:
            if file_name.endswith('.py'):
                found = os.path.join(root, file_name).replace(
                    '{0}/'.format(path), '')
                source_files.append(found)
    return source_files


class Freeze(object):

    def __init__(self, root_path):
        self.root_path = root_path
        self.logger = logger(__name__)

    def run(self):
        requirements = set()
        for file_path in find_python_files(self.root_path):
            self.logger.info('harvesting file %s', file_path)
            code = open(file_path).read()
            requirements |= set(find_imported_modules(code))

        for requirement in sorted(set(requirements).difference(sys.builtin_module_names)):
            print(requirement)

            # all_requirements.extend(file_requirements)
        # print('\n'.join(list(set(all_requirements))))
