from __future__ import absolute_import, unicode_literals, print_function
from distlib.wheel import Wheel
from .service import Service
from .signal import Signal


class Dependencer(Service):

    def __init__(self, *args, **kwargs):
        super(Dependencer, self).__init__(*args, **kwargs)
        self.dependency_found = Signal()
        self.built = Signal()

    def handle(self, requester, package, sender_data):
        # Find the wheel
        path = sender_data.pop('path')
        wheel = Wheel(path)
        run_time_dependencies = wheel.metadata.requires_dist

        for spec in run_time_dependencies:
            # Packages might declare their "extras" here, so let's split it
            dependency, extra = (';' in spec and spec or spec + ';').split(';')
            self.emit('dependency_found', self.name,
                dependency, dependency_of=package)
        else:
            self.emit('built', self.name, package, path=path)

        return {'deps': run_time_dependencies}
