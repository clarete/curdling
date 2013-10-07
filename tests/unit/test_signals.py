from mock import Mock
from curdling.signal import Signal, SignalEmitter


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


