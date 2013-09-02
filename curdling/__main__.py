from __future__ import unicode_literals, print_function

from . import Env
from .index import Index
from .util import expand_requirements

import argparse
import os


class ValidationError(Exception):
    pass


def parse_args():
    parser = argparse.ArgumentParser(
        description='Curdles your cheesy code and extracts its binaries')

    parser.add_argument(
        '-r', '--requirements',
        help='A requirements file')

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
        packages.extend([
            '{0}=={1}'.format(pkg.key, pkg.specs[0][1])
            for pkg in expand_requirements(args.requirements)
        ])

    return packages


def main():
    packages = prepare_args(parse_args())

    # Setting up the index
    path = os.path.expanduser('~/.curds')
    index = Index(path)
    index.scan()

    # Configuration values for the environment
    config = {
        'index': index,
        'urls': ['https://pypi.python.org/simple/'],
        'concurrency': 10,
        'cache_backend': {},
    }

    # Let's create the environment and start the required services
    env = Env(config)
    env.start_services()

    # Request the installation of the received package
    for pkg in packages:
        env.request_install(pkg)

    # All the installation requests were made, let's just wait here
    env.wait()


if __name__ == '__main__':
    main()
