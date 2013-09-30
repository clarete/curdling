from distlib.util import parse_requirement
from distlib.version import LegacyVersion
from .util import safe_name


def compare(operator, left_value, right_value):
    return {
        '<':  lambda l, r: l <  r,
        '>':  lambda l, r: l >  r,
        '>=': lambda l, r: l >= r,
        '<=': lambda l, r: l <= r,
    }[operator](left_value, right_value)


def combine_requirements(requirements):
    package_names = set()
    constraints = []

    lower_bound = None
    upper_bound = None

    for spec in requirements:
        requirement = parse_requirement(spec)

        # Saving all the package names to raise an exception later if the
        # user tried to return
        package_name = safe_name(requirement.name)
        package_names.add(package_name)

        # Iterate over all the constraints present in each specific
        # requirement.
        for operator, version_name in requirement.constraints or []:
            version = LegacyVersion(version_name)
            if operator == '==':
                return '{0} ({1})'.format(package_name, version)

            # do not deal with the `=` of the requirement yet. Only with both
            # `>` and `<` symbols;
            strict = len(operator) == 1
            if operator[0] == '>':
                if (not lower_bound or (version > lower_bound)) or \
                   (strict and version == lower_bound):
                    lower_bound = version
            else:
                if (not upper_bound or (version < upper_bound)) or \
                   (strict and version == upper_bound):
                    upper_bound = version
            constraints.append('{0} {1}'.format(operator, version))

    if lower_bound > upper_bound:
        raise RuntimeError('Incompatible versions')

    return '{0} ({1})'.format(list(package_names)[0], ', '.join(constraints))
