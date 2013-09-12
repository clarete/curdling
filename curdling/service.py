from __future__ import unicode_literals, print_function, absolute_import
from Queue import Queue
from .logging import ReportableError, Logger
import threading
import time


class Service(object):
    def __init__(self, **args):
        self.env = args.get('env')
        self.conf = args.pop('conf', {})
        self.index = args.pop('index', None)
        self.logger = Logger(self.name, args.get('log_level'))
        self.failures = []

        self._queue = Queue()
        self.pool = []

    @property
    def name(self):
        return self.__class__.__name__.lower()

    def queue(self, package, sender_name, **data):
        assert (sender_name == 'downloadmanager' and data.get('path')) or True
        self._queue.put((package, (sender_name, data)))
        self.logger.level(3, ' * queue(from=%s, to=%s, package=%s, data=%s)',
                          sender_name, self.name, package, data)

    def start(self):
        self.logger.level(3, ' * %s.start()', self.name)
        for worker_num in range(self.conf.get('concurrency', 10)):
            worker = threading.Thread(target=self._worker)
            worker.daemon = True
            worker.start()
            self.pool.append(worker)

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
        for package, sender_data in iter(self._queue.get, 'STOP'):
            self.logger.level(3, ' * %s.wait(%s)', self.name,
                threading.current_thread().name)

            self.logger.level(3, ' * %s.run(package=%s, sender_data=%s)',
                              self.name, package, sender_data)
            try:
                data = self.handle(package, sender_data)
                self._queue.task_done()
            except ReportableError as exc:
                self.failures.append((package, exc))
                self.logger.level(0, "Error: %s", exc)
            except BaseException as exc:
                self.failures.append((package, exc))
                self.logger.traceback(4,
                    'failed to run %s (requested by:%s) for package %s:',
                    self.name, sender_data[0], package, exc=exc)
            else:
                self.logger.level(3, ' * %s.result(package=%s): %s ... ok',
                                  self.name, package, data)
