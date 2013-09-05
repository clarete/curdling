from __future__ import absolute_import, unicode_literals, print_function
from wheel.tool import install
from .service import Service, NotForMe

import pkg_resources
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

    def find_dependencies(self, package):
        # This weird `reload()` is here cause the `get_provider` method that
        # feeds `get_distribution` uses a variable (working_set) populated in
        # the module body, so it won't get updated just by installing a new
        # package.
        name = reload(pkg_resources).Requirement.parse(package).key
        metadata = pkg_resources.get_distribution(name)._parsed_pkg_info
        dependencies = [v for k, v in metadata.items() if k == 'Requires-Dist']

        # This is another ugly thing. There's no other way for retrieving the
        # dependency list for a package until it's installed. If it is a wheel,
        # though, the dependency format will be different.
        # e.g: "ejson (==0.1.3)" will become "ejson==0.1.3"
        clear_dep = lambda d: ''.join(CONVERT_DEPENDENCY_RE.findall(d)[0])
        for dependency in dependencies:
            self.env.request_install(clear_dep(dependency))
