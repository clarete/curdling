from __future__ import absolute_import, unicode_literals, print_function
from distlib.util import parse_requirement

import io
import os
import re
import hashlib


INCLUDE_PATTERN = re.compile(r'-r\s*\b([^\b]+)')

LINK_PATTERN = re.compile(r'^([^\:]+):\/\/.+')


class AttrDict(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


def split_name(fname):
    name, ext = os.path.splitext(fname)

    try:
        ext, frag = ext.split('#')
    except ValueError:
        frag = ''
    return name, ext[1:], frag


def safe_name(spec):
    return parse_requirement(spec).requirement


def expand_requirements(file_name):
    requirements = []

    for req in io.open(file_name).read().splitlines():
        req = req.split('#', 1)[0].strip()
        if not req:
            continue

        # Handling special lines that start with `-r`, so we can have files
        # including other files.
        include = INCLUDE_PATTERN.findall(req)
        if include:
            requirements.extend(expand_requirements(include[0]))
            continue

        # Handling links, let's do nothing with this guy right now
        link = LINK_PATTERN.findall(req)
        if link:
            continue

        # Finally, we're sure that it's just a package description
        requirements.append(safe_name(req))
    return requirements


def filehash(f, algo, block_size=2**20):
    algo = getattr(hashlib, algo)()
    while True:
        data = f.read(block_size)
        if not data:
            break
        algo.update(data)
    return algo.hexdigest()
