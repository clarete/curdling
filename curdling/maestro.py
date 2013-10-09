from __future__ import absolute_import, unicode_literals, print_function
from collections import defaultdict
from distlib.version import LegacyMatcher, LegacyVersion

from . import util
from .exceptions import BrokenDependency, VersionConflict

import threading


def list_constraints(requirement):
    return (
        ', '.join(' '.join(x) for x in requirement.constraints or ()).replace('== ', '')
        or None)


def format_requirement(requirement):
    return util.parse_requirement(requirement).requirement.replace('== ', '')


def wheel_version(path):
    """Retrieve the version inside of a package data slot

    If there's no key `version` inside of the data dictionary, we'll
    try to guess the version number from the file name:

    ['forbiddenfruit', '0.1.1', 'cp27', 'none', 'macosx_10_8_x86_64.whl']
                          ^
    this is the guy we get in that crazy split!
    """
    return path.split('-')[1]


class Maestro(object):

    PENDING = 1 << 0
    FAILED  = 1 << 1

    def __init__(self):
        # This is the structure that saves all the meta-data about all the
        # requested packages. If you want to see how this structure looks like
        # when it contains actuall data.
        #
        # You should take a look in the file # `tests/unit/test_maestro.py`.
        # It contains all the possible combinations of values stored in this
        # structure.

        self.data_structure = lambda: {
            'directory': None,
            'tarball': None,
            'wheel': None,
            'exception': None,
        }

        requirement_structure = lambda: {
            'status': Maestro.PENDING,
            'dependency_of': [],
            'data': defaultdict(self.data_structure),
        }

        self.mapping = defaultdict(requirement_structure)

        # The possible states of a package
        self.status_sets = defaultdict(set)

        self.lock = threading.RLock()

    def file_requirement(self, requirement, dependency_of=None):
        requirement = format_requirement(requirement)

        with self.lock:
            entry = self.mapping[requirement]
            entry['data'] = self.data_structure()
            entry['dependency_of'].append(dependency_of)
            self.set_status(requirement, Maestro.PENDING)

    def set_status(self, requirement, status):
        [s.discard(requirement) for s in tuple(self.status_sets.values())]
        self.status_sets[status].add(requirement)
        self.mapping[requirement]['status'] = status

    def get_status(self, requirement):
        return self.mapping[requirement]['status']

    def set_data(self, requirement, field, value):
        requirement = format_requirement(requirement)
        if self.mapping[requirement]['data'][field] is not None:
            raise ValueError('Data field `{0}` is not empty'.format(field))
        self.mapping[requirement]['data'][field] = value

    def get_data(self, requirement, field):
        requirement = format_requirement(requirement)
        return self.mapping[requirement]['data'][field]

    def filter_package_by(self, status):
        result = defaultdict(list)

        def process(requirement):
            parsed = util.parse_requirement(requirement)
            return parsed.name, list_constraints(parsed)

        for requirement in self.status_sets[status]:
            name, constraints = process(requirement)
            result[name].append(constraints)

        return list(result.items())

    def get_requirements_by_package_name(self, package_name):
        return [x for x in self.mapping.keys()
            if util.parse_requirement(x).name == package_name]

    def available_versions(self, package_name):
        return sorted(set(wheel_version(self.mapping[requirement]['data']['wheel'])
            for requirement in self.mapping.keys()),
                reverse=True)

    def matching_versions(self, requirement):
        matcher = LegacyMatcher(requirement)
        package_name = util.parse_requirement(requirement).name
        versions = self.available_versions(package_name)
        return [version for version in versions if matcher.match(version)]

    def broken_versions(self, requirement):
        package_name = util.parse_requirement(requirement).name
        versions = self.available_versions(package_name)
        return [version for version in versions
            if self.get_data(requirement, 'exception')
                is not None]

    def is_primary_requirement(self, requirement):
        return not bool(filter(None, self.mapping[requirement]['dependency_of']))


    # def mark(self, attr, requirement, data):
    #     parsed = util.parse_requirement(requirement)
    #     getattr(self, attr).add(parsed.name)

    #     # The 'installed' label doesn't actually need to save any data, so we
    #     # just skip it. Going a little deeper, it's not possible cause we don't
    #     # actually have the version information when we are installing
    #     # packages. Needed to find the right bucket inside of the
    #     # project_name+version sub-dictionary structure.
    #     if data is not None:
    #         self.set_data(requirement, data)

    #     # Since we couldn't install this package, we should also mark its
    #     # requesters as failed too.
    #     if attr == 'failed':
    #         for parent in list(filter(None, self.get_parents(requirement))):
    #             self.mark('failed', parent, {
    #                 'exception': BrokenDependency(requirement),
    #             })

    # def get_parents(self, spec):
    #     requirement = util.parse_requirement(spec)
    #     versions = self.mapping[requirement.name]
    #     version = versions[constraints(requirement)]
    #     return version['dependency_of']

    # def best_version(self, package_name):
    #     versions = list(self.mapping[package_name].items())

    #     # The user didn't inform any specific version in the main requirements
    #     # (the ones received from the command line arguments, handled
    #     # above). This will be improved by fixing the issue #13.
    #     available_versions = {}
    #     for requirement_name, data in versions:
    #         version = {'name': requirement_name}
    #         version.update(data)
    #         available_versions[package_version(data['data'])] = version

    #     # The dictionary of versions collected above will become a tuple and
    #     # will be sorted (and reversed) by the version number. So, the newest
    #     # versions will be the first.
    #     available_versions = sorted(
    #         available_versions.items(),
    #         key=lambda v: package_version(v[1]['data']), reverse=True)

    #     # All requirements for this package that contain version constraints.
    #     requirements_with_constraints = list(filter(None,
    #         [v[1]['name'] for v in available_versions]))

    #     # Spec `version` might contain hyphens, like this guy: mrjob (==
    #     # 0.4-RC1) and we'll look for 0.4_RC1.
    #     spec = '{0} ({1})'.format(
    #         package_name, ', '.join(requirements_with_constraints)
    #     ).replace('-', '_')

    #     broken_dependencies = [i for i in available_versions if not i[0]]
    #     version_numbers = [i[0] for i in available_versions if i[0]]
    #     matcher = LegacyMatcher(spec)
    #     matching_versions = [v for v in version_numbers if matcher.match(v)]

    #     # May contain `BrokenDependency` instances. So, we'll have this check
    #     # below.
    #     if broken_dependencies:
    #         return broken_dependencies

    #     # We're looking for the version directly requested by the user. We
    #     # find it looking for versions that contain `None` in their field
    #     # `dependency_of`.
    #     for version, data in versions:
    #         if not list(filter(None, data['dependency_of'])):
    #             return version, data

    #     # Requirements with constraints look like "package (>= x.y.z)", while
    #     # the ones with no constraints might look just like "package". We'll
    #     # just return the first available version if none of the requirements
    #     # had constraints.
    #     if not requirements_with_constraints:
    #         return first(available_versions)

    #     # When the same package is requested more than once, we need to match
    #     # all the downloaded versions and ensure that at least one of the
    #     # downloaded versions matches _all_ requirements.
    #     if not matching_versions:
    #         raise VersionConflict(
    #             'Requirement: {0}, Available versions: {1}'.format(
    #                 spec, ', '.join(sorted(version_numbers, reverse=True))))

    #     return first(available_versions)

    # def should_queue(self, requirement):
    #     requirement = util.parse_requirement(requirement)

    #     # There might be people trying to write in our mapping and we always
    #     # need the updated values.
    #     with self.lock:
    #         currently_present = self.mapping.get(requirement.name)

    #     # If the package is not currently present in the maestro, we know that
    #     # it's safe to add it
    #     return not currently_present

    # def pending(self, set_name):
    #     return list(set(self.mapping.keys())
    #         .difference(getattr(self, set_name))
    #         .difference(self.failed))

