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

from __future__ import absolute_import, unicode_literals, print_function
from collections import defaultdict
from distlib.version import LegacyMatcher, LegacyVersion

from . import util
from .exceptions import BrokenDependency, VersionConflict


def wheel_version(path):
    """Retrieve the version inside of a package data slot

    If there's no key `version` inside of the data dictionary, we'll
    try to guess the version number from the file name:

    ['forbiddenfruit', '0.1.1', 'cp27', 'none', 'macosx_10_8_x86_64.whl']
                          ^
    this is the guy we get in that crazy split!
    """
    return path.split('-')[1]


class Mapping(object):

    def __init__(self):
        self.requirements = set()
        self.dependencies = defaultdict(list)
        self.stats = defaultdict(int)
        self.errors = defaultdict(dict)
        self.wheels = {}
        self.repeated = []

    def count(self, service):
        return self.stats[service]

    def initially_required_packages(self):
        return set(util.parse_requirement(r).name for r in self.requirements)

    def installable_packages(self):
        # Load all the wheels we built so far into the mapping, so
        # we'll be able to narrow down all the versions collected for
        # each single package to the best one.
        return set(util.parse_requirement(r).name for r in self.wheels)

    def filed_packages(self):
        return list(set(util.parse_requirement(r).name for r in self.requirements))

    def get_requirements_by_package_name(self, package_name):
        return [x for x in self.requirements
            if util.parse_requirement(x).name == util.parse_requirement(package_name).name]

    def available_versions(self, package_name):
        return sorted(set(wheel_version(self.wheels[requirement])
            for requirement in self.requirements
                if self.wheels.get(requirement) and
                    util.parse_requirement(requirement).name == package_name),
                      reverse=True)

    def matching_versions(self, requirement):
        matcher = LegacyMatcher(requirement.replace('-', '_'))
        package_name = util.parse_requirement(requirement).name
        versions = self.available_versions(package_name)
        return [version for version in versions
            if matcher.match(version)]

    def was_directly_required(self, spec):
        for requirement in self.get_requirements_by_package_name(spec):
            if self.is_primary_requirement(requirement):
                return True
        return False

    def is_primary_requirement(self, requirement):
        return bool(self.dependencies[requirement].count(None))

    def best_version(self, requirement_or_package_name, debug=False):
        package_name = util.parse_requirement(requirement_or_package_name).name
        requirements = self.get_requirements_by_package_name(package_name)

        # Used to remember in which requirement we found each version
        requirements_by_version = {}
        get_requirement = lambda v: (v, requirements_by_version[v])

        # A helper that sorts the versions putting the newest ones first
        newest = lambda versions: sorted(versions, key=LegacyVersion, reverse=True)[0]

        # Gather all version info available inside of all requirements
        all_versions = []
        all_constraints = []
        primary_versions = []
        for requirement in requirements:
            if not self.wheels.get(requirement):
                continue
            version = wheel_version(self.wheels[requirement])
            requirements_by_version[version] = requirement
            if self.is_primary_requirement(requirement):
                primary_versions.append(version)

            versions = self.matching_versions(requirement)
            all_versions.extend(versions)
            all_constraints.append(util.safe_constraints(requirement))

        # List that will gather all the primary versions. This catches
        # duplicated first level requirements with different versions.
        if primary_versions:
            return get_requirement(newest(primary_versions))

        # Find all the versions that appear in all the requirements
        compatible_versions = [v for v in all_versions
            if all_versions.count(v) == len(requirements)]

        if not compatible_versions:
            # Format the constraints string like this: " (c [, c...])"
            constraints = ', '.join(sorted(filter(None,
                all_constraints), reverse=True))
            constraints = ' ({0})'.format(constraints) if constraints else ''
            available_versions = ', '.join(sorted(
                self.available_versions(package_name),
                reverse=True))

            # Just a nice message depending on finding any versions or
            # not
            raise VersionConflict(available_versions
                and 'Requirement: {0}{1}, Available versions: {2}'.format(
                    package_name,
                    constraints,
                    available_versions,
                )
                or 'Requirement: {0}{1}, no available versions were found'.format(
                    package_name,
                    constraints,
                )
            )

        return get_requirement(newest(compatible_versions))
