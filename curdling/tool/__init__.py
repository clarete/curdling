from __future__ import absolute_import, print_function, unicode_literals
from functools import partial
from ..index import Index
from ..util import expand_requirements, safe_name, spaces, logger
from ..version import __version__
from ..services import curdler

from ..install import Install
from ..uninstall import Uninstall
from ..freeze import Freeze

import argparse
import logging
import os
import pkginfo
import sys


DEFAULT_PYPI_INDEX_LIST = [
    'https://pypi.python.org/simple/',
]


class StreamHandler(logging.StreamHandler):
    """Instantiate logging.StreamHandler correctly for Python 2.6

    The version of logging.StreamHandler in Python <2.7 is an old-style class
    that takes an argument 'strm', whereas modern Python's version is a new-
    style class that takes an argument 'stream'.
    """

    def __init__(self, stream=None):
        if sys.version_info < (2, 7):
            logging.StreamHandler.__init__(self, strm=stream)
        else:
            super(StreamHandler, self).__init__(stream=stream)


def add_parser_install(subparsers):
    parser = subparsers.add_parser(
        'install', help='Locate and install packages')
    parser.add_argument(
        '-r', '--requirements', type=argparse.FileType('r'), action='append',
        help='Parse a requirements file. Repeat as many times as you need')
    parser.add_argument(
        '-i', '--index', action='append',
        help='PyPi compatible index URL. Repeat as many times as you need')
    parser.add_argument(
        '-c', '--curdling-index', action='append', default=[],
        help='Curdling compatible index URL. Repeat as many times as you need')
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
        '-r', '--requirements', type=argparse.FileType('r'),
        help='A file listing requirements to be uninstalled')
    parser.add_argument(
        'packages', metavar='PKG', nargs='*',
        help='list of files to uninstall')
    parser.set_defaults(command='uninstall')
    return parser


def add_parser_freeze(subparsers):
    parser = subparsers.add_parser(
        'freeze',
        help='Find all the dependencies needed to run a Python software')
    parser.add_argument(
        'root_path', default=os.getcwd(), nargs='?',
        help='Root path of the codebase that neds to be analyzed')
    parser.set_defaults(command='freeze')
    return parser


def initialize_logging(log_file, log_level, log_name):
    # Set the log level for the requested logger
    handler = StreamHandler(stream=log_file)
    handler.setLevel(log_level)
    handler.setFormatter(logging.Formatter('%(asctime)s:%(name)s:%(levelname)s:%(message)s'))
    logging.getLogger(log_name).setLevel(level=log_level)
    logging.getLogger(log_name).addHandler(handler)


def get_packages_from_args(args):
    if not args.packages and not args.requirements:
        return []
    packages = [safe_name(req) for req in (args.packages or [])]
    for requirements in args.requirements or []:
        for pkg in expand_requirements(requirements):
            packages.append(pkg)
    return packages


def progress_bar(prefix, percent):
    percent_count = int(percent / 10)
    progress_bar = ('#' * percent_count) + (' ' * (10 - percent_count))
    return "\r\033[K{0}: [{1}] {2:>2}% ".format(prefix, progress_bar, percent)


def progress(phrase, total, installed, failed=0):
    percent = int((installed) / float(total) * 100.0)
    msg = [progress_bar(phrase, percent)]
    if failed:
        msg.append("({0}/{1} - {2} failed)".format(
            installed, total, failed))
    else:
        msg.append("({0}/{1})".format(installed, total))
    sys.stdout.write(''.join(msg))
    sys.stdout.flush()


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


def show_report(failed=None):
    if failed:
        sys.stdout.write('\nSome milk was spilled in the process:\n')
    else:
        sys.stdout.write('\n')
    for package, errors in list((failed or {}).items()):
        sys.stdout.write('{0}\n'.format(package))
        for requirement, data in errors.items():
            exception = data['exception']
            parents = ', '.join(
                ('from {0}'.format(d) if d else 'explicit requirement')
                for d in data['dependency_of'])
            sys.stdout.write(' * {0} {1}: {2}:\n{3}\n'.format(
                requirement,
                parents,
                exception.__class__.__name__,
                spaces(5, str(exception))))


def handle_install_exit(failed=None):
    raise SystemExit(int(failed != None))


def acceptable_file_type(filename):
    try:
        curdler.guess_file_type(filename)
        return True
    except curdler.UnpackingError:
        return False


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

    tarballs = [pkg for pkg in args.packages
                if os.path.isfile(pkg) and acceptable_file_type(pkg)]
    args.packages = [pkg for pkg in args.packages if pkg not in tarballs]
    initial_requirements = get_packages_from_args(args)

    # Callbacks that show feedback for the user
    if not args.quiet and initial_requirements:
        cmd.connect('update_retrieve_and_build', build_and_retrieve_progress)
        cmd.connect('update_install', partial(progress, 'Installing'))
        cmd.connect('update_upload', partial(progress, 'Uploading'))
        cmd.connect('finished', show_report)

    # This is the last thing called in the software. It will raise a
    # SystemExit to return the right code to the OS depending on the
    # value of received by the callback below:
    cmd.connect('finished', handle_install_exit)

    # Let's start the required services and request the installation of the
    # received packages before returning the command instance
    cmd.pipeline()
    cmd.start()
    for pkg in tarballs:
        metadata = pkginfo.SDist(pkg)
        cmd.queue(
            'main', tarball=pkg, requirement=metadata.name, directory=None)
    for pkg in initial_requirements:
        cmd.queue('main', requirement=pkg)
    return cmd


def get_uninstall_command(args):
    cmd = Uninstall({
        'log_level': args.log_level,
    })

    for pkg in get_packages_from_args(args):
        cmd.request_uninstall(pkg)
    return cmd


def get_freeze_command(args):
    return Freeze(args.root_path)


def main():
    parser = argparse.ArgumentParser(
        description='Curdles your cheesy code and extracts its binaries')

    # General arguments. All the commands have access to the following options
    if sys.version_info.major != 3:
        levels = [i for i in logging._levelNames.keys()
            if not isinstance(i, int) and i != 'NOTSET']
    else:
        levels = [i for i in logging._levelToName.keys()
            if not isinstance(i, int) and i != 'NOTSET']
    parser.add_argument(
        '-l', '--log-level', default='CRITICAL', choices=levels, type=unicode.upper,
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

    parser.add_argument(
        '-v', '--version', action='version',
        version='%(prog)s {0}'.format(__version__))

    subparsers = parser.add_subparsers()
    add_parser_install(subparsers)
    add_parser_uninstall(subparsers)
    add_parser_freeze(subparsers)
    args = parser.parse_args()

    # Let's not read the command if the user didn't inform one
    if not hasattr(args, 'command'):
        parser.error('too few arguments')

    initialize_logging(args.log_file, args.log_level, args.log_name)

    logger('main').info('curd {0}'.format(__version__))

    # Here we choose which function will be called to setup the command
    # instance that will be ran. Notice that all the `add_parser_*` functions
    # *MUST* set the variable `command` using `parser.set_defaults` otherwise
    # we'll get an error here.
    command = {
        'install': get_install_command,
        'uninstall': get_uninstall_command,
        'freeze': get_freeze_command,
    }[args.command](args)

    try:
        return command.run()
    except KeyboardInterrupt:
        raise SystemExit(0)
