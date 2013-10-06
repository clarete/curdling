from __future__ import absolute_import, print_function, unicode_literals
from ..signal import Signal, SignalEmitter
from ..util import logger
from distlib.compat import queue

import threading
import time

# See `Service._worker()`. This is the sentinel that gently stops the iterator
# over there.
SENTINEL = (None, None, {})

# Number of threads that a service will spawn by default.
DEFAULT_CONCURRENCY = 10


class Service(SignalEmitter):

    def __init__(self, **args):
        super(Service, self).__init__()

        self.env = args.get('env')
        self.conf = args.pop('conf', {})
        self.index = args.pop('index', None)
        self.logger = logger(__name__)

        # Components to implement the thread pool
        self._queue = queue.Queue()
        self.pool = []

        # Declaring signals
        self.started = Signal()
        self.finished = Signal()
        self.failed = Signal()

    def queue(self, requester, requirement, **data):
        self._queue.put((requester, requirement, data))
        self.logger.info(
            'queue(from="%s", to="%s", requirement="%s", data="%s")',
            requester, self.name, requirement, data)
        return self

    def start(self):
        self.logger.info(' * %s.start()', self.name)
        for _ in range(self.conf.get('concurrency', DEFAULT_CONCURRENCY)):
            worker = threading.Thread(target=self._worker)
            worker.daemon = True
            worker.start()
            self.pool.append(worker)
        return self

    def join(self):
        # We need to separate loops cause we can't actually tell which thread
        # got each sentinel
        for worker in self.pool:
            self._queue.put(SENTINEL)
        for worker in self.pool:
            worker.join()
        self.workers = []

    def handle(self, requester, requirement, sender_data):
        raise NotImplementedError(
            "The service subclass should override this method")

    # -- Private API --

    def _worker(self):
        # If the service consumer invokes `.queue(None, None)` it causes the
        # worker to die elegantly by matching the following sentinel:
        for requester, requirement, sender_data in iter(self._queue.get, SENTINEL):
            self.logger.debug('%s[%s].run(requirement="%s", sender_data="%s")',
                self.name, threading.current_thread().name,
                requirement, sender_data)
            try:
                self.emit('started', self.name, requirement, **sender_data)
                handler_data = self.handle(requester, requirement, sender_data) or {}
                self._queue.task_done()
            except BaseException as exception:
                self.emit('failed', self.name, requirement, exception=exception)
                self.logger.exception(
                    'failed to run %s (requested by:%s) for requirement %s:',
                    self.name, requester, requirement)
            else:
                self.emit('finished', self.name, requirement, **handler_data)
                self.logger.info('%s.result(requirement="%s"): %s ... OK',
                    self.name, requirement, handler_data)
