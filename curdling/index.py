from __future__ import absolute_import, unicode_literals, print_function
from collections import defaultdict
from pkg_resources import Requirement, parse_version, safe_name

from curdling.util import split_name

import os
import re
import shutil

FORMATS = ('whl', 'gz', 'bz', 'zip')

PKG_NAMES = [
    r'([\w\-]+)-([\d\.]+\d)[\.\-]',
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
        pkg = Requirement.parse(spec)
        msg = ['The index does not have the requested package: ']
        msg.append(pkg.key)
        msg.extend(','.join(''.join(spec) for spec in pkg.specs))
        msg.append(formats and ' ({0})'.format(formats) or '')
        super(PackageNotFound, self).__init__(''.join(msg))


class Index(object):
    def __init__(self, base_path):
        self.base_path = base_path
        self.storage = defaultdict(lambda: defaultdict(list))

    def scan(self):
        if not os.path.isdir(self.base_path):
            return

        for file_name in os.listdir(self.base_path):
            destination = os.path.join(self.base_path, file_name)
            self.index(destination)

    def ensure_path(self, destination):
        path = os.path.dirname(destination)
        if not os.path.isdir(path):
            os.makedirs(path)
        return destination

    def index(self, path):
        pkg = os.path.basename(path)
        name, version = pkg_name(pkg)
        self.storage[safe_name(name.lower())][version].append(pkg)

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

    def get(self, query):
        # Read both: "pkg==0.0.0" and "pkg==0.0.0,fmt"
        sym = ';'
        spec, format_ = (sym in query and (query.split(sym)) or (query, ''))
        requirement = Requirement.parse(spec)

        # [First step] Looking up the package name parsed from the spec
        versions = self.storage.get(requirement.key)
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
        }[op](v) for op, v in requirement.specs)

        compat_versions = filter(filter_cmp, parsed_versions.keys())
        if not compat_versions:
            raise PackageNotFound(spec, format_)

        # [Third step] Find best version to match the given format
        files = []

        # We don't have version or format, so we'll get the latest. Also,
        # we'll bring the wheels preferably, if they're available
        latest_version = versions[parsed_versions[max(compat_versions)]]
        if format_:
            files = filter(lambda n: match_format(format_, n), latest_version)
        else:
            wheels = filter(lambda n: match_format('whl', n), latest_version)
            files = wheels or latest_version

        # Unlucky, we really don't have those files
        if not files:
            raise PackageNotFound(spec, format_)

        # Yay, let's return the full path to the user
        return os.path.join(self.base_path, files[0])
