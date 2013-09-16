import threading


class Signal(list):
    pass


class SignalEmitter(object):

    def __init__(self):
        self.lock = threading.RLock()

    @property
    def name(self):
        return self.__class__.__name__.lower()

    def get_signal_or_explode(self, signal):
        try:
            with self.lock:
                return getattr(self, signal)
        except AttributeError:
            raise AttributeError(
                "There is no such signal ({0}) in this emitter ({1})".format(
                    signal, self.name))

    def connect(self, signal, callback):
        # Well, now we use the list-like interface of signal to file this new
        # callback under the previously retrieved signal container.
        self.get_signal_or_explode(signal).append(callback)

    def emit(self, signal, *args, **kwargs):
        for callback in self.get_signal_or_explode(signal):
            callback(*args, **kwargs)
