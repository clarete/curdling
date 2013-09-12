from __future__ import absolute_import, unicode_literals, print_function
from .service import Service
from .treestore import TreeStore


class Maestro(object):
    def __init__(self, *args, **kwargs):
        super(Maestro, self).__init__(*args, **kwargs)
        self.tree = TreeStore(name='root')
        self.mapping = {}

    def file_package(self, package, dependency_of):
        path = self.mapping.get(dependency_of)
        parent = path and self.tree.from_path(path) or self.tree.root
        node = self.tree.append(parent)
        self.mapping[package] = self.tree.get_path(node)
