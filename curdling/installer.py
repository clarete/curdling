from __future__ import absolute_import, unicode_literals, print_function
from pip.index import PackageFinder
from pip.req import InstallRequirement, RequirementSet
from .service import Service

import tempfile
import os


class Installer(Service):
    def __init__(self, *args, **kwargs):
        self.index = kwargs.pop('index')
        super(Installer, self).__init__(
            callback=self.install,
            *args, **kwargs)

    def install(self, package):
        # Find the package that we want to install
        source = self.index.find(package, only=('whl',))[0]

        # Create a package finder pointing to the directory that contains our
        # package. Using a package finder makes it easier to interact with the
        # PIP's `RequirementSet` API
        finder = PackageFinder(
            find_links=[os.path.dirname(source)],
            index_urls=[],
            use_wheel=True,
        )

        # This guy will unpack our package, build it and install it. Without
        # that crazy network overhead
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

        # Install all the packages (we have only one though) that can be found
        # in in our loaded finder. It contains just what we want
        requirement_set.prepare_files(finder)
        requirement_set.install([])
