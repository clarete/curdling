from __future__ import absolute_import, unicode_literals, print_function
from wheel.install import WheelFile
from .service import Service

import os


class Installer(Service):

    def handle(self, requester, package, sender_data):
        source = sender_data.pop('path')
        wheel = WheelFile(source)
        wheel.install(force=True)
