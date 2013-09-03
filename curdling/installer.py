from __future__ import absolute_import, unicode_literals, print_function
from wheel.tool import install
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
        requirements = self.index.get("{0};whl".format(package))
        wheel_dirs = [os.path.dirname(requirements)]
        install([requirements], wheel_dirs=wheel_dirs, force=True)
