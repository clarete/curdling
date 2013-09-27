from __future__ import absolute_import, unicode_literals, print_function
from collections import defaultdict
from distlib.util import parse_requirement
from distlib.version import LegacyMatcher

from . import util


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
        self.mapping[util.safe_name(requirement.name)][version] = {
            'dependency_of': dependency_of,
            'data': None,
        }

    def get_data(self, package):
        requirement = parse_requirement(package)
        version = constraints(requirement)
        return self.mapping[util.safe_name(requirement.name)][version]['data']

    def set_data(self, package, data):
        pkg = parse_requirement(package)
        version = constraints(pkg)
        self.mapping[util.safe_name(pkg.name)][version]['data'] = data

    def mark(self, attr, package, data):
        pkg = parse_requirement(package)
        getattr(self, attr).add(util.safe_name(pkg.name))

        # The 'installed' label doesn't actually need to save any data, so we
        # just skip it. Going a little deeper, it's not possible cause we don't
        # actually have the version information when we are installing
        # packages. Needed to find the right bucket inside of the
        # project_name+version sub-dictionary structure.
        if data is not None:
            self.set_data(package, data)

    def best_version(self, package_name):
        versions = self.mapping[util.safe_name(package_name)].items()

        # We're looking for the version directly requested by the user. We
        # find it looking for versions that contain `None` in their field
        # `dependency_of`.
        for version, data in versions:
            if data['dependency_of'] is None:
                return version, data

        # The user didn't inform any specific version in the main requirements
        # (the ones received from the command line arguments, handled
        # above). So, here we'll just choose the newest one. Which might be a
        # bad thing for some cases but good enough for now.
        return sorted([v for v in versions if v], reverse=True,
            key=lambda i: LegacyMatcher('{0} ({1})'.format(package_name, i[0])))[0] or versions[0]


    def should_queue(self, package):
        pkg = parse_requirement(package)
        return util.safe_name(pkg.name) not in self.mapping

    def pending(self, set_name):
        return list(set(self.mapping.keys())
            .difference(getattr(self, set_name))
            .difference(self.failed))
