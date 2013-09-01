from __future__ import absolute_import, unicode_literals, print_function
from pkg_resources import Requirement
import io
import re


INCLUDE_PATTERN = re.compile(r'-r\s*\b([^\b]+)')


def expand_requirements(file_name):
    requirements = []

    for req in io.open(file_name).read().splitlines():
        req = req.strip()
        if not req:
            break

        found = INCLUDE_PATTERN.findall(req)
        if found:
            requirements.extend(expand_requirements(found[0]))
        else:
            requirements.extend(parse_requirements(req))
    return requirements


def parse_requirements(requirements_spec):
    return [(lambda o: {
        'name': o.key,
        'spec': o.specs[0],
        'extras': [],
    })(Requirement.parse(x)) for x in requirements_spec.splitlines() if x]
