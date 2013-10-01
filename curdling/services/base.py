from __future__ import absolute_import, print_function, unicode_literals
from ..exceptions import ReportableError
from ..signal import Signal, SignalEmitter
from ..util import logger
from Queue import Queue

import threading
import time

# See `Service._worker()`. This is the sentinel that gently stops the iterator
# over there.
SENTINEL = (None, None, {})


class Service(SignalEmitter):

    def __init__(self, **args):
        super(Service, self).__init__()

        self.env = args.get('env')
        self.conf = args.pop('conf', {})
        self.index = args.pop('index', None)
        self.logger = logger(__name__)

        # Components to implement the thread pool
        self._queue = Queue()
        self.pool = []

        # Declaring signals
        self.started = Signal()
        self.finished = Signal()
        self.failed = Signal()

    def queue(self, requester, package, **data):
        self._queue.put((requester, package, data))
        self.logger.info(' * queue(from=%s, to=%s, package=%s, data=%s)',
            requester, self.name, package, data)
        return self

    def start(self):
        self.logger.info(' * %s.start()', self.name)
        for worker_num in range(self.conf.get('concurrency', 10)):
            worker = threading.Thread(target=self._worker)
            worker.daemon = True
            worker.start()
            self.pool.append(worker)
        return self

    def wait(self):
        while all(worker.is_alive() for worker in self.pool):
            time.sleep(1)

    def join(self):
        # We need to separate loops cause we can't actually tell which thread
        # got each sentinel
        for worker in self.pool:
            self._queue.put(SENTINEL)
        for worker in self.pool:
            worker.join()
        self.workers = []

    def handle(self, requester, package, sender_data):
        raise NotImplementedError(
            "The service subclass should override this method")

    # -- Private API --

    def _worker(self):
        # If the service consumer invokes `.queue(None, None)` it causes the
        # worker to die elegantly by matching the following sentinel:
        for requester, package, sender_data in iter(self._queue.get, SENTINEL):
            self.logger.debug(' * %s[%s].run(package=%s, sender_data=%s)',
                self.name, threading.current_thread().name,
                package, sender_data)
            try:
                self.emit('started', self.name, package, **sender_data)
                data = self.handle(requester, package, sender_data)
                self._queue.task_done()
            except ReportableError as exc:
                self.emit('failed', self.name, package, path=exc)
                self.logger.info(" # %s.error(): %s", self.name, exc)
                self.logger.exception(
                    'failed to run %s (requested by:%s) for package %s:',
                    self.name, requester, package)
            except BaseException as exc:
                self.emit('failed', self.name, package, path=exc)
                self.logger.exception(
                    'failed to run %s (requested by:%s) for package %s:',
                    self.name, requester, package)
            else:
                self.emit('finished', self.name, package, **(data or {}))
                self.logger.info(' * %s.result(package=%s): %s ... OK',
                    self.name, package, data)
