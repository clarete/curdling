# Curdling - Concurrent package manager for Python
# Copyright (C) 2013  Lincoln Clarete <lincoln@clarete.li>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import, print_function, unicode_literals
from collections import defaultdict
from threading import RLock
from pkg_resources import parse_version
from .util import split_name, filehash, safe_name, parse_requirement

import os
import re
import shutil

FORMATS = ('whl', 'gz', 'bz', 'zip')

PKG_NAMES = [
    r'([\w\-\_\.]+)-([\d\.]+\d)[\.\-]',
    r'(\w+)-(.+)\.\w+$',
]


def pkg_name(name):
    for expr in PKG_NAMES:
        result = re.findall(expr, name)
        if result:
            return result[0]


def match_format(format_, name):
    ext = split_name(name)[1]
    if format_.startswith('~'):
        return format_[1:] != ext
    return format_ == ext


class PackageNotFound(Exception):
    def __init__(self, spec, formats):
        pkg = parse_requirement(spec)
        msg = ['The index does not have the requested package: ']
        msg.append(pkg.requirement)
        msg.append(formats and ' ({0})'.format(formats) or '')
        super(PackageNotFound, self).__init__(''.join(msg))


class Index(object):

    def __init__(self, base_path):
        self.base_path = base_path
        self.storage = defaultdict(lambda: defaultdict(list))
        self.lock = RLock()

    def scan(self):
        if not os.path.isdir(self.base_path):
            return

        for file_name in os.listdir(self.base_path):
            destination = os.path.join(self.base_path, file_name)
            self.index(destination)

    def ensure_path(self, destination):
        path = os.path.dirname(destination)
        with self.lock:
            if not os.path.isdir(path):
                os.makedirs(path)
        return destination

    def index(self, path):
        pkg = os.path.basename(path)
        name, version = pkg_name(pkg)
        self.storage[safe_name(name)][version].append(pkg)

    def from_file(self, path):
        # Moving the file around
        file_name = '.'.join(split_name(os.path.basename(path))[:2])
        destination = self.ensure_path(os.path.join(self.base_path, file_name))
        shutil.copy(path, destination)
        self.index(destination)
        return destination

    def from_data(self, path, data):
        # Build the name of the package based on its spec and extension
        file_name = '.'.join(split_name(os.path.basename(path))[:2])
        destination = self.ensure_path(os.path.join(self.base_path, file_name))
        with open(destination, 'wb') as fobj:
            fobj.write(data)
        self.index(destination)
        return destination

    def delete(self):
        shutil.rmtree(self.base_path)

    def list_packages(self):
        return self.storage.keys()

    def get_urlhash(self, url, fmt):
        """Returns the hash of the file of an internal url
        """
        with self.open(os.path.basename(url)) as f:
            return {'url': fmt(url), 'sha256': filehash(f, 'sha256')}

    def package_releases(self, package, url_fmt=lambda u: u):
        """List all versions of a package

        Along with the version, the caller also receives the file list with all
        the available formats.
        """
        return [{
            'name': package,
            'version': version,
            'urls': [self.get_urlhash(f, url_fmt) for f in files]
        } for version, files in self.storage.get(package, {}).items()]

    def open(self, fname, mode='r'):
        return open(os.path.abspath(os.path.join(
            self.base_path, os.path.basename(fname))), mode)

    def get(self, query):
        # Read both: "pkg==0.0.0" and "pkg==0.0.0,fmt"
        sym = ';'
        spec, format_ = (sym in query and (query.split(sym)) or (query, ''))
        requirement = parse_requirement(spec)

        # [First step] Looking up the package name parsed from the spec
        versions = self.storage.get(requirement.name)
        if not versions:
            raise PackageNotFound(spec, format_)

        # [Second step] Filter out versions incompatible with our spec
        parsed_versions = {}
        [parsed_versions.update({parse_version(v): v}) for v in versions.keys()]

        filter_cmp = lambda x: all({
            '<':  lambda v: x <  parse_version(v),
            '<=': lambda v: x <= parse_version(v),
            '!=': lambda v: x != parse_version(v),
            '==': lambda v: x == parse_version(v),
            '>=': lambda v: x >= parse_version(v),
            '>':  lambda v: x >  parse_version(v),
        }[op](v) for op, v in requirement.constraints or [])

        compat_versions = [c for c in parsed_versions.keys() if filter_cmp(c)]
        if not compat_versions:
            raise PackageNotFound(spec, format_)

        # [Third step] Find best version to match the given format
        files = []

        # We don't have version or format, so we'll get the latest. Also,
        # we'll bring the wheels preferably, if they're available
        latest_version = versions[parsed_versions[max(compat_versions)]]
        if format_:
            files = [n for n in latest_version if match_format(format_, n)]
        else:
            wheels = [n for n in latest_version if match_format('whl', n)]
            files = wheels or latest_version

        # Unlucky, we really don't have those files
        if not files:
            raise PackageNotFound(spec, format_)

        # Yay, let's return the full path to the user
        return os.path.join(self.base_path, files[0])
