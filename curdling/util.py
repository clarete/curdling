from __future__ import absolute_import, print_function, unicode_literals
from distlib import compat, util

import io
import os
import re
import hashlib
import urllib3


INCLUDE_PATTERN = re.compile(r'-r\s*\b([^\b]+)')

LINK_PATTERN = re.compile(r'^([^\:]+):\/\/.+')


def split_name(fname):
    name, ext = os.path.splitext(fname)

    try:
        ext, frag = ext.split('#')
    except ValueError:
        frag = ''
    return name, ext[1:], frag


def safe_name(name):
    return name.lower().replace('_', '-')


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
        requirements.append(util.parse_requirement(req).requirement)
    return requirements


def filehash(f, algo, block_size=2**20):
    algo = getattr(hashlib, algo)()
    while True:
        data = f.read(block_size)
        if not data:
            break
        algo.update(data)
    return algo.hexdigest()


def get_auth_info_from_url(url):
    parsed = compat.urlparse(url)
    if parsed.username:
        auth = '{0}:{1}'.format(parsed.username, parsed.password)
        return urllib3.util.make_headers(basic_auth=auth)
    return {}
