from __future__ import absolute_import, unicode_literals, print_function
from collections import defaultdict
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

    def file_requirement(self, requirement, dependency_of=None):
        requirement = util.parse_requirement(requirement)
        version = constraints(requirement)

        with self.lock:
            entry = self.mapping[requirement.name][version]
            entry['dependency_of'].append(dependency_of)

    def get_data(self, requirement):
        requirement = util.parse_requirement(requirement)
        version = constraints(requirement)
        return self.mapping[requirement.name][version]['data']

    def set_data(self, requirement, data):
        requirement = util.parse_requirement(requirement)
        version = constraints(requirement)
        self.mapping[requirement.name][version]['data'] = data

    def mark(self, attr, requirement, data):
        parsed = util.parse_requirement(requirement)
        getattr(self, attr).add(parsed.name)

        # The 'installed' label doesn't actually need to save any data, so we
        # just skip it. Going a little deeper, it's not possible cause we don't
        # actually have the version information when we are installing
        # packages. Needed to find the right bucket inside of the
        # project_name+version sub-dictionary structure.
        if data is not None:
            self.set_data(requirement, data)

        # Since we couldn't install this package, we should also mark its
        # requesters as failed too.
        if attr == 'failed':
            for parent in filter(None, self.get_parents(requirement)):
                self.mark('failed', parent, BrokenDependency(requirement))

    def get_parents(self, spec):
        requirement = util.parse_requirement(spec)
        versions = self.mapping[requirement.name]
        version = versions[constraints(requirement)]
        return version['dependency_of']

    def best_version(self, package_name, debug=False):
        versions = list(self.mapping[package_name].items())

        # ['forbiddenfruit', '0.1.1', 'cp27', 'none', 'macosx_10_8_x86_64.whl']
        #                       ^
        #   this is the guy we get in that crazy split!
        package_version = lambda filename: filename.split('-')[1] \
            if not isinstance(filename, BaseException) \
            else filename

        # Return the first version inside of a list of `available_versions`
        first = lambda versions: (
            versions[0][1].pop('name'),
            versions[0][1],
        )

        # We're looking for the version directly requested by the user. We
        # find it looking for versions that contain `None` in their field
        # `dependency_of`.
        for version, data in versions:
            if not list(filter(None, data['dependency_of'])):
                return version, data

        # The user didn't inform any specific version in the main requirements
        # (the ones received from the command line arguments, handled
        # above). This will be improved by fixing the issue #13.
        available_versions = {}
        for requirement_name, data in versions:
            version = {'name': requirement_name}
            version.update(data)
            available_versions[package_version(data['data'])] = version

        # The dictionary of versions collected above will become a tuple and
        # will be sorted (and reversed) by the version number. So, the newest
        # versions will be the first.
        available_versions = sorted(
            available_versions.items(),
            key=lambda v: package_version(v[1]['data']), reverse=True)

        # If it's not a top-requirement, we still have to deal with
        # requirements without version info. If there's no version info at all,
        # we just say that we want the only version we have.
        requirement_names = list(filter(None,
            map(lambda v: v[1]['name'], available_versions)))

        # The list `requirement_names` will not be empty unless we're dealing
        # with a second-level-requirement (meaning that it's a dependency of
        # another package) and there's no version info, that happens when we
        # receive something like this:
        #
        # >>> request_install('package')  # no version like in 'package (2.0)'
        if not requirement_names:
            return first(available_versions)

        # May contain `BrokenDependency` instances. So, we'll have this check
        # below.
        version_numbers = [i[0] for i in available_versions]
        broken_dependencies = [v for v in version_numbers
            if isinstance(v, BrokenDependency)]
        if broken_dependencies:
            raise broken_dependencies[0]

        # Spec `version` might contain hyphens, like this guy: mrjob (==
        # 0.4-RC1) and we'll look for 0.4_RC1.
        spec = '{0} ({1})'.format(package_name, ', '.join(requirement_names))
        spec = spec.replace('-', '_')

        # When the same package is requested more than once, we need to match
        # all the downloaded versions and ensure that at least one of the
        # downloaded versions matches _all_ requirements.
        matcher = LegacyMatcher(spec)
        if not [v for v in version_numbers if matcher.match(v)]:
            raise VersionConflict(
                'Requirement: {0}, Available versions: {1}'.format(
                    spec, ', '.join(sorted(version_numbers, reverse=True))))

        return first(available_versions)

    def should_queue(self, requirement):
        requirement = util.parse_requirement(requirement)

        # There might be people trying to write in our mapping and we always
        # need the updated values.
        with self.lock:
            currently_present = self.mapping.get(requirement.name)

        # If the package is not currently present in the maestro, we know that
        # it's safe to add it
        return not currently_present

    def pending(self, set_name):
        return list(set(self.mapping.keys())
            .difference(getattr(self, set_name))
            .difference(self.failed))
