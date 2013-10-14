from __future__ import absolute_import, print_function, unicode_literals
from mock import Mock, ANY, call
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
    service.queue('tests')
    service.queue(None)
    service._worker()

    # Then I see that the package is indeed processed but the service dies
    # properly when it receives the sentinel.
    callback.assert_called_once_with('myservice', exception=ANY)

    # And that in the `path` parameter we receive an exception (Unfortunately
    # we can't compare NotImplementedError() instances :(
    str(callback.call_args_list[0][1]['exception']).should.equal(
        'The service subclass should override this method'
    )


def test_service_success():
    "Service#_worker() should execute self#handler() method successfully"

    # Given the following service
    class MyService(Service):
        def handle(self, requester, sender_data):
            return {'package': 'processed-package'}

    callback = Mock()
    service = MyService()
    service.connect('finished', callback)

    # When I queue one package to be processed than I queue the stop sentinel
    service.queue('tests')
    service.queue(None)
    service._worker()

    # Then I see that the right signal was emitted
    callback.assert_called_once_with('myservice', package='processed-package')


def test_service_queue_do_not_add_seen_items_when_unique():
    "Service#queue() should honor Service#unique"

    # Given the following unique service
    class MyService(Service): pass
    service = MyService(unique=True)
    service.handle = Mock(return_value={})

    # And I queue a few items
    service.queue('tests', hacker='Lincoln Clarete')
    service.queue('tests', hacker='Gabriel Falcao')

    # And I queue a repeated item
    service.queue('tests', hacker='Lincoln Clarete')

    # And I queue the sentinel to tell the service to stop
    service.queue(None)

    # When I execute the server
    service._worker()

    # Then I see that my handler was called only twice, cause we had a repeated
    # item
    list(service.handle.call_args_list).should.equal([
        call('tests', {'hacker': 'Lincoln Clarete'}),
        call('tests', {'hacker': 'Gabriel Falcao'}),
    ])


def test_service_start_join():
    "Service#join() should hang until the service is finished"

    # Given the following service
    class MyService(Service):
        def handle(self, requester, sender_data):
            return {'package': 'processed-package'}

    # And a callback connected to the 'finished' signal
    callback = Mock()
    service = MyService()
    service.connect('finished', callback)

    # When I queue the package, start and join the service
    service.queue('main')
    service.start()
    service.join()

    # Then I see that the right signal was emitted
    callback.assert_called_once_with('myservice', package='processed-package')


def test_service_call():
    "Service#__call__ should forward the execution parameters to the #handle() method"

    # Given the following service
    class MyService(Service): pass
    instance = MyService()
    instance.handle = Mock()

    # When I call an instance
    instance('service', p1='v1', p2='v2')

    # Then I see the parameters were forwarded correctly
    instance.handle.assert_called_once_with(
        'service', {'p2': 'v2', 'p1': 'v1'})
