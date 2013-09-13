from __future__ import absolute_import, unicode_literals, print_function
from distlib.database import DistributionPath
from wheel.tool import install
from .service import Service

import distlib
import tempfile
import os


class Installer(Service):

    def handle(self, requester, package, sender_data):
        source = sender_data[1].pop('path')
        wheel_dirs = [os.path.dirname(source)]
        install([source], wheel_dirs=wheel_dirs, force=True)
        self.find_dependencies(package)

    def _spec2installable(self, spec):
        pkg = distlib.database.parse_requirement(spec)
        return "{0}{1}".format(pkg.name,
            ','.join(op + v for op, v in (pkg.constraints or ())))

    def find_dependencies(self, package):
        # This nasty replace in the package name will fix the problem that
        # makes `get_distribution`
        name = distlib.database.parse_requirement(package).name
        dist = DistributionPath().get_distribution(name.replace('_', '-'))

        # This is another ugly thing. There's no other way for retrieving the
        # dependency list for a package until it's installed. If it is a wheel,
        # though, the dependency format will be different.
        # e.g: "ejson (==0.1.3)" will become "ejson==0.1.3"
        for dependency in dist.requires.union(dist.test_requires):
            self.env.request_install(
                self._spec2installable(dependency),
                sender=self.name, data={'dependency-of': package})
