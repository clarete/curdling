from __future__ import absolute_import, print_function, unicode_literals
from mock import Mock, ANY
from curdling.services.base import Service


def test_service():
    "Service#_worker() should stop when hitting the sentinel"

    # Given the following service
    class MyService(Service):
        pass

    callback = Mock()
    service = MyService()
    service.connect('failed', callback)

    # When I queue one package to be processed than I queue the stop sentinel
    service.queue('main', 'package')
    service.queue(None, None)
    service._worker()

    # Then I see that the package is indeed processed but the service dies
    # properly when it receives the sentinel.
    callback.assert_called_once_with('myservice', 'package', exception=ANY)

    # And that in the `path` parameter we receive an exception (Unfortunately
    # we can't compare NotImplementedError() instances :(
    str(callback.call_args_list[0][1]['exception']).should.equal(
        'The service subclass should override this method'
    )


def test_service_success():
    "Service#_worker() should execute self#handler() method successfully"

    # Given the following service
    class MyService(Service):
        def handle(self, requester, package, sender_data):
            return {'package': 'processed-package'}

    callback = Mock()
    service = MyService()
    service.connect('finished', callback)

    # When I queue one package to be processed than I queue the stop sentinel
    service.queue('main', 'package')
    service.queue(None, None)
    service._worker()

    # Then I see that the right signal was emitted
    callback.assert_called_once_with(
        'myservice', 'package', package='processed-package')


def test_service_start_join():
    "Service#join() should hang until the service is finished"

    # Given the following service
    class MyService(Service):
        def handle(self, requester, package, sender_data):
            return {'package': 'processed-package'}

    # And a callback connected to the 'finished' signal
    callback = Mock()
    service = MyService()
    service.connect('finished', callback)

    # When I queue the package, start and join the service
    service.queue('main', 'package')
    service.start()
    service.join()

    # Then I see that the right signal was emitted
    callback.assert_called_once_with(
        'myservice', 'package', package='processed-package')

