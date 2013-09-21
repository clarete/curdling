from __future__ import absolute_import, unicode_literals, print_function
from collections import defaultdict
from distlib.util import parse_requirement


def constraints(requirement):
    return (
        ','.join(' '.join(x) for x in requirement.constraints or ())
        or None)


class Maestro(object):

    def __init__(self, *args, **kwargs):
        super(Maestro, self).__init__(*args, **kwargs)
        self.mapping = defaultdict(dict)

        # The possible states of a package
        self.failed = set()
        self.retrieved = set()
        self.built = set()
        self.installed = set()

    def file_package(self, package, dependency_of=None):
        requirement = parse_requirement(package)
        version = constraints(requirement)
        self.mapping[requirement.name.lower()][version] = {
            'dependency_of': dependency_of,
            'data': None,
        }

    def get_data(self, package):
        requirement = parse_requirement(package)
        version = constraints(requirement)
        return self.mapping[requirement.name.lower()][version]['data']

    def set_data(self, package, data):
        pkg = parse_requirement(package)
        version = constraints(pkg)
        self.mapping[pkg.name.lower()][version]['data'] = data

    def mark(self, attr, package, data):
        pkg = parse_requirement(package)
        name = pkg.name.lower()
        getattr(self, attr).add(name)

        # The 'installed' label doesn't actually need to save any data, so we
        # just skip it. Going a little deeper, it's not possible cause we don't
        # actually have the version information when we are installing
        # packages. Needed to find the right bucket inside of the
        # project_name+version sub-dictionary structure.
        if data is not None:
            self.set_data(package, data)

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

    def pending(self, set_name):
        return list(set(self.mapping.keys())
            .difference(getattr(self, set_name))
            .difference(self.failed))
