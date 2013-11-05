from __future__ import absolute_import, unicode_literals, print_function
from ..signal import Signal
from .. import util
from .base import Service
from distlib.wheel import Wheel


class Dependencer(Service):

    def __init__(self, *args, **kwargs):
        super(Dependencer, self).__init__(*args, **kwargs)
        self.ignore_extra = kwargs.get('ignore_extra')
        self.dependency_found = Signal()

    def handle(self, requester, data):
        requirement = data['requirement']
        wheel = Wheel(data['wheel'])
        run_time_dependencies = wheel.metadata.requires_dist

        for spec in run_time_dependencies:
            # Packages might declare their "extras" here, so let's split it
            dependency, extra = (';' in spec and spec or spec + ';').split(';')
            if extra and self.ignore_extra:
                continue
            self.emit('dependency_found', self.name,
                      requirement=util.safe_name(dependency),
                      dependency_of=requirement)
        return {'requirement': requirement, 'wheel': data['wheel']}
