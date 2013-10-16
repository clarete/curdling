from __future__ import absolute_import, print_function, unicode_literals
from functools import partial
from ..index import Index
from ..util import expand_requirements, safe_name, spaces

from ..install import Install
from ..uninstall import Uninstall

import argparse
import logging
import os
import sys


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
        help='Upload packages back to the curdling index')
    parser.add_argument(
        '-f', '--force', action='store_true', default=False,
        help='Skip checking if the requirement requested is already installed')
    parser.add_argument(
        'packages', metavar='REQUIREMENT', nargs='*',
        help='list of requirements to install')
    parser.set_defaults(command='install')
    return parser


def add_parser_uninstall(subparsers):
    parser = subparsers.add_parser(
        'uninstall', help='Uninstall packages')
    parser.add_argument(
        '-r', '--requirements',
        help='A file listing requirements to be uninstalled')
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

def progress_bar(prefix, percent):
    percent_count = percent / 10
    progress_bar = ('#' * percent_count) + (' ' * (10 - percent_count))
    return "\r\033[K{0}: [{1}] {2:>2}% ".format(prefix, progress_bar, percent)


def build_and_retrieve_progress(total, retrieved, built, failed):
    processed = built + failed
    percent = int((processed) / float(total) * 100.0)
    msg = [progress_bar('Retrieving', percent)]
    if failed:
        info = "({0} requested, {1} retrieved, {2} built, {3} failed)"
        msg.append(info.format(total, retrieved, built, failed))
    else:
        msg.append("({0} requested, {1} retrieved, {2} processed)".format(
            total, retrieved, built))
    sys.stdout.write(''.join(msg))
    sys.stdout.flush()


def progress(phrase, total, installed):
    percent = int((installed) / float(total) * 100.0)
    msg = [progress_bar(phrase, percent)]
    msg.append("({0}/{1})".format(installed, total))
    sys.stdout.write(''.join(msg))
    sys.stdout.flush()


def show_report(failed=None):
    if failed:
        sys.stdout.write('\nSome milk was spilled in the process:\n')
    else:
        sys.stdout.write('\n')
    for package, errors in list((failed or {}).items()):
        sys.stdout.write('{0}\n'.format(package))
        for data in errors:
            exception = data['exception']
            parents = ', '.join((d or 'explicit') for d in data['dependency_of'])
            sys.stdout.write(' * {0} from {1}: {2}:\n{3}\n'.format(
                data['requirement'],
                parents,
                exception.__class__.__name__,
                spaces(5, str(exception))))


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

    # Callbacks that show feedback for the user
    if not args.quiet:
        cmd.connect('update_retrieve_and_build', build_and_retrieve_progress)
        cmd.connect('update_install', partial(progress, 'Installing'))
        cmd.connect('update_upload', partial(progress, 'Uploading'))
        cmd.connect('finished', show_report)

    # Let's start the required services and request the installation of the
    # received packages before returning the command instance
    cmd.pipeline()
    cmd.start()
    for pkg in get_packages_from_args(args):
        cmd.feed('main', requirement=pkg)
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

    levels = filter(lambda x: not isinstance(x, int), logging._levelNames.keys())
    parser.add_argument(
        '-l', '--log-level', default='CRITICAL', choices=levels,
        help='Log verbosity level (for nerds): {0}'.format(', '.join(levels)))

    parser.add_argument(
        '--log-file', type=argparse.FileType('w'), default=sys.stderr,
        help='File to write the log')

    parser.add_argument(
        '--log-name', default=None,
        help=(
            'Name of the logger you want to set the level with '
            '`-l` (for the nerdests)'
        ))

    parser.add_argument(
        '-q', '--quiet', action='store_true', default=False,
        help='No output unless combined with `-l\'')

    subparsers = parser.add_subparsers()
    add_parser_install(subparsers)
    add_parser_uninstall(subparsers)
    args = parser.parse_args()

    # Set the log level for the requested logger
    handler = logging.StreamHandler(stream=args.log_file)
    handler.setLevel(args.log_level)
    handler.setFormatter(logging.Formatter('%(asctime)s:%(name)s:%(levelname)s:%(message)s'))
    logging.getLogger(args.log_name).setLevel(level=args.log_level)
    logging.getLogger(args.log_name).addHandler(handler)

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
