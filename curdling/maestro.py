from __future__ import absolute_import, unicode_literals, print_function
from collections import defaultdict
from distlib.util import parse_requirement
from .service import Service
from .treestore import TreeStore


class Maestro(object):

    def __init__(self, *args, **kwargs):
        super(Maestro, self).__init__(*args, **kwargs)
        self.tree = TreeStore(name='root')
        self.mapping = defaultdict(dict)
        self.built = set()

    def file_package(self, package, dependency_of=None):
        # Reading the package description
        requirement = parse_requirement(package)
        version = (
            ''.join(' '.join(x) for x in requirement.constraints or [])
            or None)

        # Trying to find the package's parent inside of our internal
        # mapping. If we can't find it, we'll use the root node
        path = self.mapping.get(dependency_of)
        parent = path and self.tree.from_path(path and path[None]) or self.tree.root
        node = self.tree.append(parent)

        # Saving back to the mapping
        self.mapping[requirement.name].update({
            version: self.tree.get_path(node),
        })

    def mark_built(self, package):
        self.built.add(parse_requirement(package).name)

    @property
    def pending_packages(self):
        return list(set(self.mapping.keys()).difference(self.built))
