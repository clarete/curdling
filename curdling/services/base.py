from __future__ import absolute_import, print_function, unicode_literals
from ..signal import Signal, SignalEmitter
from ..util import logger
from distlib.compat import queue

import sys
import threading
import time
import traceback

# See `Service._worker()`. This is the sentinel that gently stops the iterator
# over there.
SENTINEL = (None, {})

# Number of threads that a service will spawn by default.
DEFAULT_CONCURRENCY = 2


class Service(SignalEmitter):

    def __init__(self, size=DEFAULT_CONCURRENCY, **args):
        super(Service, self).__init__()

        self.size = size
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

    def queue(self, requester, **data):
        self.logger.debug('%s.queue(from="%s", data="%s")', self.name, requester, data)
        self._queue.put((requester, data))
        return self

    def start(self):
        self.logger.debug('%s.start()', self.name)
        for _ in range(self.size):
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
            except BaseException:
                fname, lineno, fn, text = traceback.extract_tb(sys.exc_info()[2])[0]
                self.logger.exception(
                    '%s.run(from="%s", data="%s") failed:\n'
                    '%s:%d (%s) %s',
                    name, requester, sender_data,
                    fname, lineno, fn, text,
                )
                sender_data.update(exception=sys.exc_info()[1])
                self.emit('failed', self.name, **sender_data)
            else:
                self.logger.debug('%s.run(data="%s"): %s', name, sender_data, result)
                self.emit('finished', self.name, **result)
