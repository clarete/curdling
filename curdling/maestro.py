from __future__ import absolute_import, unicode_literals, print_function
from collections import defaultdict
from distlib.util import parse_requirement
from distlib.version import LegacyVersion, LegacyMatcher

from . import util
from .lib import combine_requirements
from .exceptions import BrokenDependency, VersionConflict

import threading


def constraints(requirement):
    return (
        ','.join(' '.join(x) for x in requirement.constraints or ())
        or None)


class Maestro(object):

    def __init__(self):
        # This is the structure that saves all the meta-data about all the
        # requested packages. If you want to see how this structure looks like
        # when it contains actuall data.
        #
        # You should take a look in the file # `tests/unit/test_maestro.py`.
        # It contains all the possible combinations of values stored in this
        # structure.
        self.mapping = defaultdict(
            lambda: defaultdict(
                lambda: dict(dependency_of=[], data=None)))

        # The possible states of a package
        self.failed = set()
        self.retrieved = set()
        self.built = set()
        self.installed = set()

        self.lock = threading.RLock()

    def file_package(self, package, dependency_of=None):
        requirement = parse_requirement(package)
        version = constraints(requirement)

        with self.lock:
            entry = self.mapping[util.safe_name(requirement.name)][version]
            entry['dependency_of'].append(dependency_of)

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

        # Since we couldn't install this package, we should also mark its
        # requesters as failed too.
        if attr == 'failed':
            for parent in filter(None, self.get_parents(package)):
                self.mark('failed', parent, BrokenDependency(package))

    def get_parents(self, spec):
        requirement = parse_requirement(spec)
        versions = self.mapping[util.safe_name(requirement.name)]
        version = versions[constraints(requirement)]
        return version['dependency_of']

    def best_version(self, package_name):
        versions = self.mapping[util.safe_name(package_name)].items()

        # We're looking for the version directly requested by the user. We
        # find it looking for versions that contain `None` in their field
        # `dependency_of`.
        for version, data in versions:
            if not filter(None, data['dependency_of']):
                return version, data

        # The user didn't inform any specific version in the main requirements
        # (the ones received from the command line arguments, handled
        # above). This will be improved by fixing the issue #13.
        requirement_names = []
        available_versions = set()
        for requirement_name, data in versions:
            # We don't really know how to deal with this kind of thing here
            if isinstance(data['data'], BaseException):
                continue

            # ['forbiddenfruit', '0.1.1', 'cp27', 'none', 'macosx_10_8_x86_64.whl']
            #                       ^
            #   this is the guy we get in that crazy split!
            available_versions.add(data['data'].split('-')[1])
            requirement_names.append(requirement_name)

        # If it's not a top-requirement, we still have to deal with
        # requirements without version info. If there's no version info at all,
        # we just say that we want the only version we have.
        requirement_names = filter(None, requirement_names)

        # The list `requirement_names` will not be empty unless we're dealing
        # with a second-level-requirement (meaning that it's a dependency of
        # another package) and there's no version info, that happens when we
        # receive something like this:
        #
        # >>> request_install('package')  # no version like in 'package (2.0)'
        if not requirement_names:
            return versions[0]

        # Spec `version` might contain hyphens, like this guy: mrjob (==
        # 0.4-RC1) and we'll look for 0.4_RC1.
        spec = '{0} ({1})'.format(package_name, ', '.join(requirement_names))
        spec = spec.replace('-', '_')

        matcher = LegacyMatcher(spec)
        compatible_versions = [v for v in available_versions if matcher.match(v)]
        if not compatible_versions:
            raise VersionConflict(
                'Requirement: {0}, Available versions: {1}'.format(
                    spec, ', '.join(available_versions)))

        return versions[0]

    def should_queue(self, requirement):
        parsed_requirement = parse_requirement(requirement)
        package_name = util.safe_name(parsed_requirement.name)

        # There might be people trying to write in our mapping and we always
        # need the updated values.
        with self.lock:
            currently_present = self.mapping.get(package_name)

        # If the package is not currently present in the maestro, we know that
        # it's safe to add it
        return not currently_present

    def pending(self, set_name):
        return list(set(self.mapping.keys())
            .difference(getattr(self, set_name))
            .difference(self.failed))
