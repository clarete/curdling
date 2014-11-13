from __future__ import absolute_import, print_function, unicode_literals

import io
import logging
import mock

from collections import namedtuple
from curdling import tool


def test_get_packages_from_empty_args():
    "get_packages_from_args() Should return an empty list when no package spec can be found in `args' "

    # Given that I have an argument bag with no package specs
    args = namedtuple('args', ['packages', 'requirements'])(
        packages=None, requirements=None)

    # When I expand the package list
    packages = tool.get_packages_from_args(args)

    # Then I see I've got nothing!
    packages.should.be.empty


def test_get_packages_from_args():
    "get_packages_from_args() Should find out all the package names specified in `packages`"

    # Given that I have an argument bag with package specs
    args = namedtuple('args', ['packages', 'requirements'])(
        packages=['sure', 'milieu'], requirements=None)

    # When I expand the package list
    packages = tool.get_packages_from_args(args)

    # Then I see I've got the packages I specified
    packages.should.equal(['sure', 'milieu'])


def test_get_packages_requirement_from_args():
    "get_packages_from_args() Should expand all the packages specified in `requirements`"

    requirements = io.StringIO('sure==0.2.1\nmilieu==0.1.7')
    requirements2 = io.StringIO('python-dateutil')

    # Given that I have an argument bag with package specs
    args = namedtuple('args', ['packages', 'requirements'])(
        packages=None, requirements=[requirements, requirements2])

    # When I expand the package list
    packages = tool.get_packages_from_args(args)

    # Then I see I've got the packages I specified
    packages.should.equal([
        'sure (0.2.1)', 'milieu (0.1.7)', 'python-dateutil'])


def test_initialize_logging():
    """This test just ensures tool.initialize_logging does not raise an
    exception, as happened on Python 2.6 before ab7fc12f
    """
    with mock.patch.object(logging, 'getLogger'):
        tool.initialize_logging(
            log_file=mock.sentinel.log_file,
            log_level=logging.DEBUG,
            log_name=mock.sentinel.log_name,
        )

def test_base_parser_accepts_a_logging_level():
    "main() should accept a `--log-level` argument"
    parser = tool.base_parser()
    try:
        args = parser.parse_args(['-l', bytes('debug')])
    except SystemExit:
        assert False, 'args not parsed correctly'

    assert args.log_level == 'DEBUG'
