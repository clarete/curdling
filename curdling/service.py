from __future__ import unicode_literals, print_function, absolute_import
from gevent.pool import Pool
from gevent.queue import Queue
import traceback
import gevent
import sys


class Service(object):
    def __init__(self, callback, concurrency=1, result_queue=None, env=None):
        self.callback = callback
        self.result_queue = result_queue
        self.package_queue = Queue()
        self.failed_queue = []
        self.env = env

        self.main_greenlet = None
        self.pool = Pool(concurrency)
        self.should_run = True

        self.subscribers = []

    def queue(self, package):
        print(' * {0},queueing: {1}'.format(self.__class__.__name__.lower(), package))
        self.package_queue.put(package)

    def consume(self):
        package = self.package_queue.get()
        print(' * {0},consuming: {1}'.format(self.__class__.__name__.lower(), package))
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
        except BaseException as exc:
            self.failed_queue.append((package, exc))

            # The programmer (or user) might need some feedback
            frames = traceback.extract_tb(sys.exc_info()[2])
            print('failed to run {0} for package {1}: {2}. TB:'.format(
                self.__class__.__name__, package, exc))
            for frame in reversed(frames):
                print(' {0}:{1} {2}(): {3}'.format(*frame))
        else:
            # Let's notify our subscribers
            for subscriber in self.subscribers:
                subscriber.queue(package)

            # If the callback worked, let's go ahead and tell the world. If and
            # only if requested by the caller, of course.
            if self.result_queue:
                self.result_queue.put(package)
