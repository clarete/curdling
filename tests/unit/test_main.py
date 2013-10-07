from __future__ import absolute_import, print_function, unicode_literals
from mock import call, patch, Mock, ANY
from curdling.services.base import Service
from curdling.signal import Signal, SignalEmitter

# -- Signals --

def test_signal():
    "It should possible to emit signals"

    # Given that I have a button that emits signals
    class Button(SignalEmitter):
        clicked = Signal()

    # And a content to store results of the callback function associated with
    # the `clicked` signal in the next lines
    callback = Mock()

    # And an instance of that button class
    b = Button()
    b.connect('clicked', callback)

    # When button instance gets clicked (IOW: when we emit the `clicked`
    # signal)
    b.emit('clicked', a=1, b=2)

    # Then we see that the  dictionary was populated as expected
    callback.assert_called_once_with(a=1, b=2)


def test_signal_that_does_not_exist():
    "AttributeError must be raised if a given signal does not exist"

    # Given that I have a button that emits signals, but with no signals
    class Button(SignalEmitter):
        pass

    # And an instance of that button class
    b = Button()

    # When I try to connect an unknown signal to the instance, Then I see
    # things just explode with a nice message.
    b.connect.when.called_with('clicked', lambda *a: a).should.throw(
        AttributeError,
        'There is no such signal (clicked) in this emitter (button)',
    )


# -- Signals --


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

