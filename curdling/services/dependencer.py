from __future__ import absolute_import, unicode_literals, print_function
from ..signal import Signal
from .. import util
from .base import Service
from distlib.wheel import Wheel


class Dependencer(Service):

    def __init__(self, *args, **kwargs):
        super(Dependencer, self).__init__(*args, **kwargs)
        self.dependency_found = Signal()

    def handle(self, requester, data):
        requirement = data['requirement']
        dependencies = Wheel(data['wheel']).metadata.dependencies
        extra_sections = set(util.parse_requirement(requirement).extras or ())

        # Honor the `extras` section of the requirement we just received
        found = dependencies.get('install', [])
        for section, items in dependencies.get('extras', {}).items():
            if section in extra_sections:
                found.extend(items)

        # Telling the world about the dependencies we found
        for dependency in found:
            self.emit('dependency_found', self.name,
                      requirement=util.safe_name(dependency),
                      dependency_of=requirement)

        # Keep the message flowing
        return {'requirement': requirement, 'wheel': data['wheel']}
