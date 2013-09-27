from __future__ import absolute_import, print_function, unicode_literals
from ..index import Index
from ..util import expand_requirements, safe_name

from ..install import Install
from ..uninstall import Uninstall

import logging
import argparse
import os


DEFAULT_PYPI_INDEX_LIST = [
    'http://pypi.python.org/simple/',
]


def add_parser_install(subparsers):
    parser = subparsers.add_parser(
        'install', help='Locate and install packages')
    parser.add_argument(
        '-r', '--requirements',
        help='A requirements file')
    parser.add_argument(
        '-i', '--index', action='append',
        help='PyPi compatible index url. Repeat as many times as you need')
    parser.add_argument(
        '-c', '--curdling-index', action='append', default=[],
        help='Curdling compatible index url. Repeat as many times as you need')
    parser.add_argument(
        '-u', '--upload', action='store_true', default=False,
        help='Upload your packages back to the curdling index')
    parser.add_argument(
        '-f', '--force', action='store_true', default=False,
        help='Skip checking if the package requested is already installed')
    parser.add_argument(
        'packages', metavar='PKG', nargs='*',
        help='list of files to install')
    parser.set_defaults(command='install')
    return parser


def add_parser_uninstall(subparsers):
    parser = subparsers.add_parser(
        'uninstall', help='Locate and uninstall packages')
    parser.add_argument(
        '-r', '--requirements',
        help='A requirements file listing packages to be uninstalled')
    parser.add_argument(
        'packages', metavar='PKG', nargs='*',
        help='list of files to uninstall')
    parser.set_defaults(command='uninstall')
    return parser


def get_packages_from_args(args):
    if not args.packages and not args.requirements:
        return []

    packages = [safe_name(req) for req in (args.packages or [])]
    if args.requirements:
        for pkg in expand_requirements(args.requirements):
            packages.append(pkg)
    return packages


def get_install_command(args):
    index = Index(os.path.expanduser('~/.curds'))
    index.scan()

    cmd = Install({
        'log_level': args.log_level,
        'pypi_urls': args.index or DEFAULT_PYPI_INDEX_LIST,
        'curdling_urls': args.curdling_index,
        'force': args.force,
        'upload': args.upload,
        'index': index,
    })

    # Let's start the required services and request the installation of the
    # received packages before returning the command instance
    cmd.start_services()
    for pkg in get_packages_from_args(args):
        cmd.request_install('main', pkg)
    return cmd


def get_uninstall_command(args):
    cmd = Uninstall({
        'log_level': args.log_level,
    })

    for pkg in get_packages_from_args(args):
        cmd.request_uninstall(pkg)
    return cmd


def main():
    parser = argparse.ArgumentParser(
        description='Curdles your cheesy code and extracts its binaries')

    # General arguments. All the commands have access to the following options
    parser.add_argument(
        '-l', '--log-level', default=1, type=int,
        help=(
            'Increases the verbosity, goes from 0 (quiet) to '
            'the infinite and beyond (chatty)'))

    parser.add_argument(
        '-d', '--debug', default='CRITICAL',
        help='Library debug level (for nerds)',
        choices=filter(lambda x: not isinstance(x, int),
            logging._levelNames.values()))

    subparsers = parser.add_subparsers()
    add_parser_install(subparsers)
    add_parser_uninstall(subparsers)
    args = parser.parse_args()

    # Enable debug if requested by user
    logging.basicConfig(level=args.debug)

    # Here we choose which function will be called to setup the command
    # instance that will be ran. Notice that all the `add_parser_*` functions
    # *MUST* set the variable `command` using `parser.set_defaults` otherwise
    # we'll get an error here.
    command = {
        'install': get_install_command,
        'uninstall': get_uninstall_command,
    }[args.command](args)

    try:
        return command.run()
    except KeyboardInterrupt:
        print('\b\b')
        command.report()
        raise SystemExit(0)
