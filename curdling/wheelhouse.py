from __future__ import absolute_import, unicode_literals, print_function
import tempfile
import os
import shutil

from pip.req import InstallRequirement, RequirementSet
from pip.index import PackageFinder
from pip.wheel import WheelBuilder

from .service import Service


class Curdling(Service):
    def __init__(self, *args, **kwargs):
        self.index = kwargs.pop('index', None)
        super(Curdling, self).__init__(
            callback=self.wheel,
            *args, **kwargs)

    def wheel(self, package):
        source = self.index.get("{0};~whl".format(package))
        target = os.path.dirname(source)

        # The package finder is what PIP uses to find packages given their
        # names. This finder won't use internet at all, only the folder we know
        # that our file is.
        finder = PackageFinder(find_links=[target], index_urls=[])

        # Another requirement to use PIP API, we have to build a requirement
        # set.
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

        # Here we go, we're finally converting the package from a regular
        # format to a wheel. Notice that the wheel dir is another tmp
        # directory. See comments below.
        wheel_dir = tempfile.mkdtemp()
        builder = WheelBuilder(
            requirement_set,
            finder,
            wheel_dir=wheel_dir,
            build_options=[],
            global_options=[],
        )
        builder.build()

        # Since I just can't retrieve the brand new file name through the API,
        # the wheel dir is a tmp directory so the *only* file over there *is*
        # the one that we want.
        wheel_file = os.listdir(wheel_dir)[0]
        path = self.index.from_file(os.path.join(wheel_dir, wheel_file))

        # Cleaning up the mess. Here I kill the two temp folders I created to
        # 1) build the package into a wheel, 2) output the wheel file
        # separately
        shutil.rmtree(build_dir)
        shutil.rmtree(wheel_dir)

        # Finally, we just say where in the storage the file is
        return os.path.join(os.path.dirname(source), wheel_file)
