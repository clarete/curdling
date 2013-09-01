from __future__ import absolute_import, unicode_literals, print_function
from pkg_resources import Requirement

import io
import os
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
            requirements.append(Requirement.parse(req))
    return requirements


def gen_package_path(package_name):
    path = list(package_name[:2])
    path.append(Requirement.parse(package_name).key)
    return os.path.join(*path)


class LocalCache(object):
    def __init__(self, backend):
        self.backend = backend

    def push(self, name):
        self.backend[name] = gen_package_path(name)

    def get(self, pkg):
        return self.backend.get(pkg)


class Env(object):
    def __init__(self, local_cache_backend):
        self.local_cache = LocalCache(backend=local_cache_backend)

    def request_install(self, requirement):
        if self.check_installed(requirement):
            return True

        elif self.local_cache.get(requirement):
            self.install_queue.put(requirement)
            return False

        self.download_queue.put(requirement)
        return False
