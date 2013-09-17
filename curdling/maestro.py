from __future__ import absolute_import, unicode_literals, print_function
from collections import defaultdict
from distlib.util import parse_requirement
from .service import Service


def constraints(requirement):
    return (
        ','.join(' '.join(x) for x in requirement.constraints or ())
        or None)


class Maestro(object):

    def __init__(self, *args, **kwargs):
        super(Maestro, self).__init__(*args, **kwargs)
        self.mapping = defaultdict(dict)
        self.built = set()
        self.failed = set()

    def file_package(self, package, dependency_of=None):
        requirement = parse_requirement(package)
        version = constraints(requirement)
        self.mapping[requirement.name.lower()][version] = {
            'dependency_of': dependency_of,
            'data': None,
        }

    def _mark(self, attr, package, data):
        pkg = parse_requirement(package)
        name = pkg.name.lower()
        getattr(self, attr).add(name)
        self.mapping[name][constraints(pkg)]['data'] = data

    def mark_built(self, package, data):
        self._mark('built', package, data)

    def mark_failed(self, package, data):
        self._mark('failed', package, data)

    def get_data(self, package):
        requirement = parse_requirement(package)
        version = constraints(requirement)
        return self.mapping[requirement.name.lower()][version]['data']

    def best_version(self, package_name):
        versions = self.mapping[package_name].items()

        # We're looking for the version directly requested by the user. We
        # find it looking for versions that contain `None` in their field
        # `dependency_of`.
        for version, data in versions:
            if data['dependency_of'] is None:
                return version, data

        # There's no hard feelings about versions here. Meaning that the user
        # didn't request this package as a primary installation target.
        return versions[0]

    def should_queue(self, package):
        pkg = parse_requirement(package)
        return pkg.name.lower() not in self.mapping

    @property
    def pending_packages(self):
        return list(set(self.mapping.keys())
            .difference(self.built)
            .difference(self.failed))
