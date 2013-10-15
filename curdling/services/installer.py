from __future__ import absolute_import, print_function, unicode_literals
from ..util import parse_requirement
from .base import Service
from distlib.wheel import Wheel

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

    def handle(self, requester, data):
        name = parse_requirement(data['requirement']).name
        wheel = Wheel(data['wheel'])
        wheel.install(get_distribution_paths(name))
        return data
