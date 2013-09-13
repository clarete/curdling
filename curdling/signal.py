class Signal(list):
    pass


class SignalEmitter(object):

    @property
    def name(self):
        return self.__class__.__name__.lower()

    def get_signal_or_explode(self, signal):
        try:
            return getattr(self, signal)
        except AttributeError:
            raise AttributeError(
                "There is no such signal({0} in this emitter({1})",
                signal, self.name)

    def connect(self, signal, callback):
        # Well, now we use the list-like interface of signal to file this new
        # callback under the previously retrieved signal container.
        self.get_signal_or_explode(signal).append(callback)

    def emit(self, signal, *args, **kwargs):
        print(' + {0}.emit({1}, args={2}, kw={3})'.format(
            self.name, signal, args, kwargs))
        for callback in self.get_signal_or_explode(signal):
            callback(*args, **kwargs)
