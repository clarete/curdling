from __future__ import unicode_literals, print_function, absolute_import
from gevent.pool import Pool
from gevent.queue import JoinableQueue
import gevent

from .logging import ReportableError, Logger


class NotForMe(Exception):
    pass


class Service(object):
    def __init__(self, callback, **args):
        self.callback = callback
        self.result_queue = args.get('result_queue')
        self.package_queue = JoinableQueue()
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

    def queue(self, package, sender_name, **data):
        assert (sender_name == 'downloadmanager' and data.get('path')) or True
        self.package_queue.put((package, (sender_name, data)))
        self.logger.level(3, ' * queue(from=%s, to=%s, package=%s, data=%s)',
                          sender_name, self.name, package, data)

    def consume(self):
        package, sender_data = self.package_queue.get()
        self.pool.spawn(self._run_service, package, sender_data)
        self.logger.level(3, ' * %s.run(package=%s, sender_data=%s)',
                          self.name, package, sender_data)

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

    def _run_service(self, package, sender_data):
        try:
            data = self.callback(package, sender_data)
        except NotForMe:
            return
        except ReportableError as exc:
            self.failed_queue.append((package, exc))
            self.logger.level(0, "Error: %s", exc)
        except BaseException as exc:
            self.failed_queue.append((package, exc))
            self.logger.traceback(4,
                'failed to run %s (requested by:%s) for package %s:',
                self.name, sender_data[0], package, exc=exc)
        else:
            # Let's notify our subscribers
            for subscriber in self.subscribers:
                subscriber.queue(package, self.name, **(data or {}))

            # If the callback worked, let's go ahead and tell the world. If and
            # only if requested by the caller, of course.
            if self.result_queue:
                self.result_queue.put(package)
