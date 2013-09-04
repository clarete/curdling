from __future__ import unicode_literals, print_function, absolute_import
from gevent.pool import Pool
from gevent.queue import Queue
import gevent

from .logging import ReportableError, Logger


class Service(object):
    def __init__(self, callback, **args):
        self.callback = callback
        self.result_queue = args.get('result_queue')
        self.package_queue = Queue()
        self.failed_queue = []
        self.env = args.get('env')

        self.main_greenlet = None
        self.pool = Pool(args.get('concurrency'))
        self.should_run = True

        self.subscribers = []
        self.logger = Logger(self.name, args.get('log_level'))

    @property
    def name(self):
        return self.__class__.__name__.lower()

    def queue(self, package):
        self.logger.level(3, ' * %s,queueing: %s', self.name, package)
        self.package_queue.put(package)

    def consume(self):
        package = self.package_queue.get()
        self.logger.level(3, ' * %s,consuming: %s', self.name, package)
        self.pool.spawn(self._run_service, package)

    def subscribe(self, other):
        other.subscribers.append(self)

    def loop(self):
        while self.should_run:
            self.consume()

    def start(self):
        self.main_greenlet = gevent.spawn(self.loop)

    def stop(self, force=False):
        # This will force the current iteraton on `loop()` to be the last one,
        # so the thing we're processing will be able to finish;
        self.should_run = False

        # if the caller is in a hurry, we'll just kill everything mercilessly
        if force and self.main_greenlet:
            self.main_greenlet.kill()

    def _run_service(self, package):
        try:
            self.callback(package)
        except ReportableError as exc:
            self.failed_queue.append((package, exc))
            self.logger.level(0, "Error: %s", exc)
        except BaseException as exc:
            self.failed_queue.append((package, exc))
            self.logger.traceback(4,
                'failed to run %s for package %s:',
                self.name, package, exc=exc)
        else:
            # Let's notify our subscribers
            for subscriber in self.subscribers:
                subscriber.queue(package)

            # If the callback worked, let's go ahead and tell the world. If and
            # only if requested by the caller, of course.
            if self.result_queue:
                self.result_queue.put(package)
