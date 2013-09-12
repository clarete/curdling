from __future__ import unicode_literals, print_function, absolute_import
from Queue import Queue
from multiprocessing.pool import ThreadPool
from .logging import ReportableError, Logger
import threading
import time


class Service(object):
    def __init__(self, **args):
        self.env = args.get('env')
        self.conf = args.pop('conf', {})
        self.index = args.pop('index', None)
        self.logger = Logger(self.name, args.get('log_level'))

        self.pool = ThreadPool(args.get('concurrency', 1))
        self.lock = threading.RLock()
        self.async_result = None
        self._queue = Queue()

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
        self.async_result = self.pool.apply_async(self._run_service)

    def terminate(self):
        self.pool.terminate()
        self.pool.join()

    def wait(self):
        while not self.async_result.ready():
            time.sleep(1)

    def join(self):
        self.pool.close()
        self.pool.join()

    # -- Private API --

    def _run_service(self):
        while True:
            package, sender_data = self._queue.get()

            self.logger.level(3, ' * %s.run(package=%s, sender_data=%s)',
                              self.name, package, sender_data)
            try:
                data = self.handle(package, sender_data)
            except ReportableError as exc:
                self.failed_queue.append((package, exc))
                self.logger.level(0, "Error: %s", exc)
            except BaseException as exc:
                self.failed_queue.append((package, exc))
                self.logger.traceback(4,
                    'failed to run %s (requested by:%s) for package %s:',
                    self.name, sender_data[0], package, exc=exc)

            self.logger.level(3, ' * %s.result(package=%s): %s ... ok',
                              self.name, package, data)
