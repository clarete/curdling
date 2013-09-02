from __future__ import absolute_import, unicode_literals, print_function
from pip.index import PackageFinder
from pip.req import InstallRequirement, RequirementSet
from pip.wheel import move_wheel_files
from . import Service

import tempfile
import os


class Installer(Service):
    def __init__(self, *args, **kwargs):
        self.storage = kwargs.pop('storage', None)
        super(Installer, self).__init__(
            callback=self.install,
            *args, **kwargs)

    def install(self, package):
        source = self.storage.find(package, allowed=('.whl',))[0]
        target = os.path.join(self.storage.path, os.path.dirname(source))
        finder = PackageFinder(
            find_links=[target],
            index_urls=[],
            use_wheel=True,
        )
        build_dir = tempfile.mkdtemp()
        requirement_set = RequirementSet(
            build_dir=build_dir,
            src_dir=None,
            download_dir=None,
            download_cache=None,
            ignore_dependencies=True,
            ignore_installed=True,
        )
        requirement_set.add_requirement(
            InstallRequirement.from_line(package))

        requirement_set.prepare_files(finder)
        requirement_set.install([])
