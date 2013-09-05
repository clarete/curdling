from __future__ import unicode_literals, print_function

from . import Env
from .index import Index
from .util import expand_requirements, AttrDict

import argparse
import os


DEFAULT_PYPI_INDEX_LIST = [
    'https://pypi.python.org/simple/',
]


class ValidationError(Exception):
    pass


def parse_args():
    parser = argparse.ArgumentParser(
        description='Curdles your cheesy code and extracts its binaries')

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

    return parser.parse_args()


def prepare_args(args):
    if args.packages is None and args.requirements is None:
        raise ValidationError(
            'we need either at least one package or a requirements file')

    packages = args.packages or []
    if args.requirements:
        for pkg in expand_requirements(args.requirements):
            packages.append(str(pkg))

    return AttrDict(
        packages=packages,
        pypi_urls=args.index or DEFAULT_PYPI_INDEX_LIST,
        curdling_urls=args.curdling_index,
        upload=args.upload,
        log_level=args.log_level,
    )


def prepare_env():
    args = prepare_args(parse_args())

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
    env = Env(args)
    env.start_services()

    # Request the installation of the received package
    for pkg in args.packages:
        env.request_install(pkg)

    return env


def err_code(errors):
    # This function defines what's the error number that curdling will return!
    # Yeah, it's a big deal! It's just a stub though. For now, this naive
    # implementation returns success if no installations failed.
    return errors.get('install', 0)


def __run():
    env = prepare_env()
    try:
        # All the installation requests were made, let's just wait here
        env.wait()
    except KeyboardInterrupt:
        print('\b\bIs there cheese in your rug?')
        raise SystemExit(err_code(env.shutdown()))
    return {}


if __name__ == '__main__':
    raise SystemExit(err_code(__run()))
