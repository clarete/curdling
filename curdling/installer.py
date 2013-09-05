from __future__ import absolute_import, unicode_literals, print_function
from distlib.database import DistributionPath
from wheel.tool import install
from .service import Service, NotForMe

import distlib
import tempfile
import os
import re


CONVERT_DEPENDENCY_RE = re.compile(r'([\w\_\-]+)\b\s*\(?([^\)]+)?')


class Installer(Service):
    def __init__(self, *args, **kwargs):
        self.index = kwargs.pop('index')
        super(Installer, self).__init__(
            callback=self.install,
            *args, **kwargs)

    def install(self, package, sender_data):
        source = sender_data[1].pop('path')

        # If the file is not a wheel, then we bail. We don't know how to
        # install anything else anything :)
        if not re.findall('whl$', source):
            raise NotForMe

        wheel_dirs = [os.path.dirname(source)]
        install([source], wheel_dirs=wheel_dirs, force=True)
        self.find_dependencies(package)

    def _spec2installable(self, spec):
        pkg = distlib.database.parse_requirement(spec)
        return "{0}{1}".format(pkg.name,
            ','.join(op + v for op, v in pkg.constraints))

    def find_dependencies(self, package):
        # This weird `reload()` is here cause the `get_provider` method that
        # feeds `get_distribution` uses a variable (working_set) populated in
        # the module body, so it won't get updated just by installing a new
        # package.
        name = distlib.database.parse_requirement(package).name
        dist = DistributionPath().get_distribution(name)

        # This is another ugly thing. There's no other way for retrieving the
        # dependency list for a package until it's installed. If it is a wheel,
        # though, the dependency format will be different.
        # e.g: "ejson (==0.1.3)" will become "ejson==0.1.3"
        for dependency in dist.requires.union(dist.test_requires):
            self.env.request_install(
                self._spec2installable(dependency),
                sender=self.name, data={'dependency-of': package})
