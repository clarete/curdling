from __future__ import absolute_import, print_function, unicode_literals
from distlib.util import parse_requirement
from distlib.version import LegacyVersion, LegacyMatcher
from .util import safe_name


def combine_requirements(requirements):
    constraints = set()
    strict_versions = set()

    lower_bound = None
    upper_bound = None

    for spec in requirements:
        requirement = parse_requirement(spec)
        package_name = safe_name(requirement.name)
        found_constraints = requirement.constraints or []

        # Iterate over all the constraints present in each strict
        # requirement.
        for operator, version_name in found_constraints:
            version = LegacyVersion(version_name)
            version_str = '{0} {1}'.format(operator, version)

            # Saving the list of requested versions. It's slightly different to
            # save strict versions cause we don't want to append the strict
            # version to the constraint list without being able to filter it
            # out later. Cause the `constraints` variable here just holds
            # references to all the versions we need to compare;
            #
            # Check the variable `combined_version` in the end of this function
            # and you'll see that building the final string that describes the
            # version found and comparing the compatibility between those
            # versions is a separate work.
            constraints.add(version_str)

            if operator == '==':
                strict_versions.add(version_str)
            elif operator[0] == '>':
                lower_bound = version
            else:
                upper_bound = version

    # If the user informed more than one `strict` versions we should just
    # fail. Since we're using `set`s to manage strict_versions, duplications
    # will be ignored.
    if len(strict_versions) > 1:
        raise RuntimeError('Incompatible versions')
    if len(strict_versions) == 1:
        strict_version_number = list(strict_versions)[0].split()[1]

    # We need to separate the version number from the package name to apply the
    # logic that determines if we're good or not. This helper is just an easy
    # way to build the package name again.
    full_name = lambda constraint: '{0} ({1})'.format(package_name, constraint)

    # This code won't run unless we're dealing with both strict and range
    # versions. It will basically make sure that the strict version will be the
    # chosen one. However, we have to make sure that it is compatible to all
    # the other versions requested.
    if strict_versions and constraints.difference(strict_versions):
        compatible_versions = [
            LegacyMatcher(full_name(c)).match(strict_version_number)
            for c in constraints]
        if all(compatible_versions):
            return full_name(strict_version_number)
        raise RuntimeError('Incompatible versions')

    # There's no need to validate the version boundaries when we have only one
    # version to join
    if len(constraints) == 1:
        return full_name(list(constraints)[0])

    # The following comparison will tell if we're requiring two incompatible
    # versions.
    if lower_bound > upper_bound:
        raise RuntimeError('Incompatible versions')

    # The user requested specific versions of the requirement we're dealing
    # with. They must be compatible among each other and compatible with the
    # other requested versions.
    combined_version = strict_versions and strict_version_number or \
        ', '.join(constraints.difference(strict_versions))
    return full_name(combined_version)
