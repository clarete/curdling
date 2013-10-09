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

    class Status:
        PENDING   = 0
        RETRIEVED = 1 << 0
        BUILT     = 1 << 1
        INSTALLED = 1 << 2
        FAILED    = 1 << 3

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
            'status': Maestro.Status.PENDING,
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
            self.set_status(requirement, Maestro.Status.PENDING)

    def set_status(self, requirement, status):
        self.mapping[requirement]['status'] = status

    def add_status(self, requirement, status):
        self.set_status(requirement, self.get_status(requirement) | status)

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

    def filter_by(self, status):
        return [key for key in self.mapping.keys()
            if self.get_status(key) & status]

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

    def best_version(self, requirement_or_package_name, debug=False):
        package_name = util.parse_requirement(requirement_or_package_name).name
        requirements = self.get_requirements_by_package_name(package_name)

        # A helper that sorts the versions putting the newest ones first
        newest = lambda versions: sorted(versions, reverse=True)[0]

        # Gather all version info available inside of all requirements
        all_versions = []
        all_constraints = []
        primary_versions = []
        for requirement in requirements:
            if self.is_primary_requirement(requirement):
                version = wheel_version(self.get_data(requirement, 'wheel'))
                primary_versions.append(version)

            all_versions.extend(self.matching_versions(requirement))
            all_constraints.append(list_constraints(util.parse_requirement(requirement)))

        # List that will gather all the primary versions. This catches
        # duplicated first level requirements with different versions.
        if primary_versions:
            return newest(primary_versions)

        # Find all the versions that appear in all the requirements
        compatible_versions = [v for v in all_versions
            if all_versions.count(v) == len(requirements)]

        if not compatible_versions:
            raise VersionConflict(
                'Requirement: {0} ({1}), Available versions: {2}'.format(
                    package_name,
                    ', '.join(all_constraints),
                    ', '.join(self.available_versions(package_name)),
                ))

        return newest(compatible_versions)
