from __future__ import unicode_literals, print_function
from sh import pip

import argparse
import os

from . import hash_files, CurdException, CurdManager
from .server import Server


def main():
    parser = argparse.ArgumentParser(
        description='Curdles your cheesy code and extracts its binaries')
    parser.add_argument(
        '-H', '--show-hash', action='store_true',
        help='Shows the SHA1 hash of a list of concatenated files')

    parser.add_argument(
        '-r', '--remote-cache-url',
        help='The address for a remote curdle cache')

    parser.add_argument(
        '-p', '--pypi-url',
        help=('The address for a pypi server. Will be forwarded to pip '
              'as the argument `--index-url`'))

    parser.add_argument(
        '-p2', '--pypi-url-2',
        help=('A fallback address for a pypi server. Will be forwarded to pip '
              'as the argument `--extra-index-url`'))

    parser.add_argument(
        '-s', '--server',
        help=('Spins up a server to share curds'))

    parser.add_argument(
        'files', metavar='FILE', nargs='+',
        help='List of pip requirements files')

    args = parser.parse_args()

    path = os.path.join(os.getcwd(), '.curds')

    settings = {}

    # The user doesn't need anything else, but the hash of the files
    if args.show_hash:
        return print(hash_files(args.files))

    if args.pypi_url:
        settings['index-url'] = args.pypi_url

    if args.pypi_url_2:
        settings['extra-index-url'] = args.pypi_url_2

    # Creating the manager that points to the `.curds` directory inside of the
    # current path. After that we add the files received from the command line
    # arguments.
    manager = CurdManager(path, settings)
    uid = manager.add(args.files)

    # Accessing the local cache
    curd = manager.get(uid)
    if not curd:
        print('[info] No cache found')

    # Acessing the remote cache
    if not curd and not args.remote_cache_url:
        print('[info] No external cache informed, using pip to curdle')
    elif not curd:
        print('[info] Looking for curds in the given url')
        manager.settings.update({'cache-url': args.remote_cache_url})
        curd = manager.retrieve(uid)

    # Building our own curd
    if not curd:
        print('[info] Curdling')
        try:
            curd = manager.new(uid)
        except CurdException as exc:
            print('[error]')
            print(exc)
            return

    # Spawning the server!
    if args.server:
        host, port = args.server.split(':')
        try:
            Server(manager, __name__).run(debug=True, host=host, port=int(port))
        except KeyboardInterrupt:
            return

    # Installing the curdled dependencies
    print('[info] Installing curdled packages')
    try:
        manager.install(uid)
    except CurdException as exc:
        print('[error]')
        print(exc)
        return
