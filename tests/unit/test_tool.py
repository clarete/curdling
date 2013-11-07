from __future__ import absolute_import, print_function, unicode_literals

import logging

import mock
from mock import Mock

from curdling import tool


def test_initialize_logging():
    with mock.patch.object(logging, 'getLogger'):
        tool.initialize_logging(
            log_file=mock.sentinel.log_file,
            log_level=logging.DEBUG,
            log_name=mock.sentinel.log_name,
        )
