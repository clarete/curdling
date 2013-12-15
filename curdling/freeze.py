import ast
import imp
import os
import sys
from distlib.database import DistributionPath


class ImportVisitor(ast.NodeVisitor):

    def __init__(self):
        self.imports = []

    def visit_Import(self, node):
        self.imports.append(node.names[0].name)

    def visit_ImportFrom(self, node):
        self.imports.append(node.module)


def find_imported_modules(code):
    visitor = ImportVisitor()
    visitor.visit(ast.parse(code))
    return list(filter(None, visitor.imports))


def get_module_path(module_name):
    module_path = imp.find_module(module_name)[1]
    possible_paths = []
    for path in sys.path:
        if path in module_path:
            possible_paths.append(path)
    return module_path.replace(
        '{0}/'.format(max(possible_paths)), '')


def get_distribution_from_source_file(file_name):
    path = DistributionPath(include_egg=True)
    distribution = path.get_distribution(
        os.path.dirname(file_name) or file_name)
    return distribution


def get_requirements(code):
    def format_module(module_name):
        path = get_module_path(module_name)
        distribution = get_distribution_from_source_file(path)
        return '{0}=={1}'.format(
            distribution.name,
            distribution.version)

    return [format_module(m)
        for m in find_imported_modules(code)]
