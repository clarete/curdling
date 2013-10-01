from __future__ import absolute_import, unicode_literals, print_function
from collections import defaultdict
from distlib.util import parse_requirement
from distlib.version import LegacyMatcher

from . import util
from .lib import combine_requirements
from .exceptions import BrokenDependency


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

    def file_package(self, package, dependency_of=None):
        requirement = parse_requirement(package)
        version = constraints(requirement)
        entry = self.mapping[util.safe_name(requirement.name)][version]
        if dependency_of is not None:
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
            for parent in self.get_parents(package):
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
            if data['dependency_of'] is None:
                return version, data

        # The user didn't inform any specific version in the main requirements
        # (the ones received from the command line arguments, handled
        # above). This will be improved by fixing the issue #13.
        return versions[0]

    def should_queue(self, requirement):
        parsed_requirement = parse_requirement(requirement)
        package_name = util.safe_name(parsed_requirement.name)
        currently_present = self.mapping.get(package_name)

        # If the package is not currently present in the maestro, we know that
        # it's safe to add it
        if not currently_present:
            return True

        # Now let's retrieve all the versions requested so far and see if any
        # of them match the request we're dealing with right now. If it does
        # match, we don't need to add the same requirement again.
        versions = currently_present.keys()

        # Do not add requirements without version info if there's any other
        # version already filled.
        if not parsed_requirement.constraints and versions:
            return False

        # Ensuring that we always prefer packages with version information:
        #
        # Knowing that when the caller files a package without version info,
        # we'll use `None` as the version key. That said, we have to remove
        # this version before comparing things.
        versions.count(None) and versions.remove(None)
        combined_requirements = combine_requirements([requirement])
        matcher = LegacyMatcher(combined_requirements)
        return (not any(matcher.match(v) for v in versions))

    def pending(self, set_name):
        return list(set(self.mapping.keys())
            .difference(getattr(self, set_name))
            .difference(self.failed))
