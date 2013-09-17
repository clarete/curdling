from __future__ import absolute_import, unicode_literals, print_function
from distlib.wheel import Wheel
from distlib.util import parse_requirement
from .service import Service

import sys
import os.path


PREFIX = os.path.normpath(sys.prefix)


def get_distribution_paths(name):
    """Return target paths where the package content should be installed"""
    pyver = 'python' + sys.version[:3]

    paths = {
        'prefix' : '{prefix}',
        'data'   : '{prefix}/lib/{pyver}/site-packages',
        'purelib': '{prefix}/lib/{pyver}/site-packages',
        'platlib': '{prefix}/lib/{pyver}/site-packages',
        'headers': '{prefix}/include/{pyver}/{name}',
        'scripts': '{prefix}/bin',
    }

    # pip uses a similar path as an alternative to the system's (read-only)
    # include directory:
    if hasattr(sys, 'real_prefix'):  # virtualenv
        paths['headers'] = os.path.abspath(
            os.path.join(sys.prefix, 'include', 'site', pyver, name))

    # Replacing vars
    for key, val in paths.items():
        paths[key] = val.format(prefix=PREFIX, name=name, pyver=pyver)
    return paths


class Installer(Service):

    def handle(self, requester, package, sender_data):
        source = sender_data.pop('path')
        name = parse_requirement(package).name
        wheel = Wheel(source)
        wheel.install(get_distribution_paths(name))
