from __future__ import absolute_import, unicode_literals, print_function
from collections import defaultdict
from pkg_resources import Requirement

from curdling.util import split_name

import os
import re
import shutil

FORMATS = ('whl', 'gz', 'bz', 'zip')

PKG_NAME = lambda n: re.findall(r'([\w\_\.]+)-([\d\.]+\d)[\.\-]', n)[0]


def key_from_path(path):
    return '{0}=={1}'.format(*PKG_NAME(os.path.basename(path)))


def name_from_key(spec, ext):
    # Add tar. to `bz` and `gz` files
    ext = ext in ('gz', 'bz') and 'tar.' + ext or ext

    # Parse the requirement and build the new name
    req = Requirement.parse(spec)
    name = [req.key]
    name.append('-')
    name.append(req.specs[0][1])
    name.append('.')
    name.append(ext)
    return ''.join(name)


class Index(object):
    def __init__(self, base_path):
        self.base_path = base_path
        self.storage = defaultdict(list)

    def scan(self):
        if not os.path.isdir(self.base_path):
            return

        for file_name in os.listdir(self.base_path):
            key = key_from_path(file_name)
            destination = os.path.join(self.base_path, file_name)
            self.storage[key].append(destination)

    def ensure_path(self, destination):
        path = os.path.dirname(destination)
        if not os.path.isdir(path):
            os.makedirs(path)
        return destination

    def from_file(self, path):
        # Moving the file around
        destination = self.ensure_path(os.path.join(self.base_path, os.path.basename(path)))
        shutil.copy(path, destination)

        # Indexing the saved path under the `key` extracted from the package
        # name.
        key = key_from_path(path)
        self.storage[key].append(destination)

    def from_data(self, package, ext, data):
        # Build the name of the package based on its spec and extension
        file_name = name_from_key(package, ext)
        destination = self.ensure_path(os.path.join(self.base_path, file_name))
        with open(destination, 'wb') as fobj:
            fobj.write(data)
        self.storage[package].append(destination)

    def find(self, spec, only=FORMATS):
        return filter(lambda f: split_name(f)[1] in only, self.storage[spec])

    def delete(self):
        shutil.rmtree(self.base_path)
