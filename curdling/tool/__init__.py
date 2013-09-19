from __future__ import absolute_import, print_function, unicode_literals
from ..index import Index
from ..util import expand_requirements, safe_name, AttrDict
from ..install import Install

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
        '-l', '--log-level', default=1, type=int,
        help=(
            'Increases the verbosity, goes from 0 (quiet) to '
            'the infinite and beyond (chatty)'))
    parser.add_argument(
        'packages', metavar='PKG', nargs='*',
        help='list of files to install')
    return parser


def build_parser():
    parser = argparse.ArgumentParser(
        description='Curdles your cheesy code and extracts its binaries')
    subparsers = parser.add_subparsers()
    add_parser_install(subparsers)
    return parser.parse_args()


def prepare_args(args):
    if not args.packages and not args.requirements:
        raise

    packages = [safe_name(req) for req in (args.packages or [])]
    if args.requirements:
        for pkg in expand_requirements(args.requirements):
            packages.append(pkg)

    return AttrDict(
        packages=packages,
        pypi_urls=args.index or DEFAULT_PYPI_INDEX_LIST,
        curdling_urls=args.curdling_index,
        upload=args.upload,
        log_level=args.log_level,
    )


def prepare_env():
    args = prepare_args(build_parser())

    # Setting up the index
    path = os.path.expanduser('~/.curds')
    index = Index(path)
    index.scan()

    # Configuration values for the environment
    args.update({
        'index': index,
        'concurrency': 10,
    })

    # Let's create the environment and start the required services
    env = Install(args)
    env.start_services()

    # Request the installation of the received package
    for pkg in args.packages:
        env.request_install('main', pkg)

    return env


def main():
    env = prepare_env()
    try:
        # All the installation requests were made, let's just wait here
        return env.run()
    except KeyboardInterrupt:
        print('\b\b')
        env.report()
        raise SystemExit(0)
