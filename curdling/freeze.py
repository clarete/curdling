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
    def format_module(module_name):
        try:
            path = get_module_path(module_name)
        except ImportError:
            return

        # If we do have a module that matches tha name we still need
        # to know if it was installed as a package. If it was not, we
        # consider that the user is not interested in adding this
        # package to the requirements list, so we just skip it.
        distribution = get_distribution_from_source_file(path)
        if not distribution:
            return

        # Let's build the output in a format that everybody
        # understands
        return '{0}=={1}'.format(
            distribution.name,
            distribution.version)

    return list(filter(None, [format_module(m)
        for m in find_imported_modules(code)]))


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

    def run(self):
        requirements = []
        for file_path in find_python_files(self.root_path):
            file_requirements = get_requirements(open(file_path).read())
            requirements.extend(file_requirements)
        print('\n'.join(list(set(requirements))))
