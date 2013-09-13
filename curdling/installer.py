from __future__ import absolute_import, unicode_literals, print_function
from wheel.tool import install
from .service import Service

import os


class Installer(Service):

    def handle(self, requester, package, sender_data):
        source = sender_data.pop('path')
        wheel_dirs = [os.path.dirname(source)]
        install([source], wheel_dirs=wheel_dirs, force=True)
