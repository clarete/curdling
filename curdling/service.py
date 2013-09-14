from __future__ import unicode_literals, print_function, absolute_import
from Queue import Queue
from .logging import ReportableError, Logger
from .signal import Signal, SignalEmitter

import threading
import time


class Service(SignalEmitter):

    def __init__(self, **args):
        super(Service, self).__init__()

        self.env = args.get('env')
        self.conf = args.pop('conf', {})
        self.index = args.pop('index', None)
        self.logger = Logger(self.name, args.get('log_level'))

        # Components to implement the thread pool
        self._queue = Queue()
        self.pool = []

        # Declaring signals
        self.started = Signal()
        self.finished = Signal()
        self.failed = Signal()

    def queue(self, requester, package, **data):
        self._queue.put((requester, package, data))
        self.logger.level(3, ' * queue(from=%s, to=%s, package=%s, data=%s)',
            requester, self.name, package, data)
        return self

    def start(self):
        self.logger.level(3, ' * %s.start()', self.name)
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
            self._queue.put('STOP')  # Sending a sentinel
        for worker in self.pool:
            worker.join()
        self.workers = []

    # -- Private API --

    def _worker(self):
        for requester, package, sender_data in iter(self._queue.get, 'STOP'):
            self.logger.level(3, ' * %s[%s].run(package=%s, sender_data=%s)',
                self.name, threading.current_thread().name,
                package, sender_data)
            try:
                self.emit('started', self.name, package, **sender_data)
                data = self.handle(requester, package, sender_data)
                self._queue.task_done()
            except ReportableError as exc:
                self.emit('failed', self.name, package, path=exc)
                self.logger.level(0, " # %s.error(): %s", self.name, exc)
            except BaseException as exc:
                self.emit('failed', self.name, package, path=exc)
                self.logger.traceback(4,
                    'failed to run %s (requested by:%s) for package %s:',
                    self.name, requester, package)
            else:
                self.emit('finished', self.name, package, **(data or {}))
                self.logger.level(3, ' * %s.result(package=%s): %s ... ok',
                    self.name, package, data)
