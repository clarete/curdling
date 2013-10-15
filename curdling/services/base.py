from __future__ import absolute_import, print_function, unicode_literals
from ..signal import Signal, SignalEmitter
from ..util import logger
from distlib.compat import queue

import threading
import time

# See `Service._worker()`. This is the sentinel that gently stops the iterator
# over there.
SENTINEL = (None, {})

# Number of threads that a service will spawn by default.
DEFAULT_CONCURRENCY = 10


class Service(SignalEmitter):

    def __init__(self, **args):
        super(Service, self).__init__()

        self.env = args.get('env')
        self.conf = args.pop('conf', {})
        self.index = args.pop('index', None)
        self.logger = logger(__name__)

        # Uniqueness
        self.unique = args.get('unique', False)
        self.seen = set()

        # Components to implement the thread pool
        self._queue = queue.Queue()
        self.pool = []

        # Declaring signals
        self.started = Signal()
        self.finished = Signal()
        self.failed = Signal()

    def queue(self, requester, **data):
        key = tuple(data.items())
        if key in self.seen and (requester, data) != SENTINEL:
            self.logger.debug('%s.skip.queue(from="%s", data="%s"): key: %s',
                self.name, requester, data, key)
            return self
        self.seen.add(key)
        self.logger.debug('%s.queue(from="%s", data="%s")', self.name, requester, data)
        self._queue.put((requester, data))
        return self

    def start(self):
        self.logger.debug('%s.start()', self.name)
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

    def handle(self, requester, sender_data):
        raise NotImplementedError(
            "The service subclass should override this method")

    def __call__(self, requester, **kwargs):
        return self.handle(requester, kwargs)

    # -- Private API --

    def _worker(self):
        name = '{0}[{1}]'.format(self.name, threading.current_thread().name)

        # If the service consumer invokes `.queue(None, None)` it causes the
        # worker to die elegantly by matching the following sentinel:
        for requester, sender_data in iter(self._queue.get, SENTINEL):
            self.logger.debug('%s.run(data="%s")', name, sender_data)
            try:
                self.emit('started', self.name, **sender_data)
                result = self(requester, **sender_data) or {}
                self._queue.task_done()
            except BaseException as exception:
                self.logger.exception('%s.run(from="%s", data="%s") failed',
                    name, requester, sender_data)
                sender_data.update(exception=exception)
                self.emit('failed', self.name, **sender_data)
            else:
                self.logger.debug('%s.run(data="%s"): %s', name, sender_data, result)
                self.emit('finished', self.name, **result)
