from __future__ import absolute_import, unicode_literals, print_function
from pkg_resources import Requirement

from pip.req import InstallRequirement
from pip.index import PackageFinder

import io
import os
import re

import urllib2

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


class PipSource(object):
    def __init__(self, dirs=None, urls=None):
        self.finder = PackageFinder(
            find_links=dirs or [],
            index_urls=urls or [])

    def url(self, package):
        return self.finder.find_requirement(
            InstallRequirement.from_line(package),
            True).url


class DownloadManager(object):
    def __init__(self, sources=None, storage=None):
        self.sources = sources
        self.storage = storage

    def download(self, package_name, url):
        pkg = urllib2.urlopen(url).read()
        path = gen_package_path(package_name)
        return self.storage.write(path, pkg)

    def retrieve(self, package):
        for source in self.sources:
            pkg = self.download(package, source.url(package))
            return pkg
        return False
