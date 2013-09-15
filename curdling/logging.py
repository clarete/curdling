from __future__ import unicode_literals, print_function, absolute_import
import traceback
import sys


class ReportableError(Exception):
    pass


class Logger(object):
    def __init__(self, name, run_level):
        self.name = name
        self.run_level = run_level or 200  # Will run with tests

    def level(self, level, msg, *args, **kwargs):
        indent = kwargs.get('indent')
        kind = kwargs.get('kind')

        if kind == 'traceback':
            indent = 4
        elif kind == 'error':
            indent = 2

        if indent:
            msg = '\n'.join(
                '{0}{1}'.format(' ' * indent, x)
                for x in msg.splitlines())

        if level <= self.run_level:
            print(msg % args, end=kwargs.get('end', '\n'))

    def traceback(self, level, msg, *args, **kwargs):
        # Print out banner
        exc = kwargs.get('exc')
        msg = msg if not exc else \
            "{0} ({1}: {2})".format(msg, exc.__class__.__name__, exc)
        self.level(level, msg, *args, kind='error')

        # Than the last traceback
        frames = traceback.extract_tb(sys.exc_info()[2])
        for frame in reversed(frames):
            self.level(level,
                ' %s:%s %s(): %s', *frame,
                indent=4, kind='traceback')

