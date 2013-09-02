from __future__ import absolute_import, unicode_literals, print_function
from pkg_resources import Requirement

import io
import os
import re


INCLUDE_PATTERN = re.compile(r'-r\s*\b([^\b]+)')



def split_name(fname):
    name, ext = os.path.splitext(fname)

    try:
        ext, frag = ext.split('#')
    except ValueError:
        frag = ''
    return name, ext[1:], frag


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
            requirements.append(Requirement.parse(req))
    return requirements
