from __future__ import unicode_literals, print_function
from curdling import hash_files, CurdManager
from curdling.server import Server
from sh import pip
import argparse
import os


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
        help=('The address for a pypi installation '
              'that will be used if no `-r` is passed'))

    parser.add_argument(
        '-s', '--server',
        help=('Spins up a server to share curds'))

    parser.add_argument(
        'files', metavar='FILE', nargs='+',
        help='List of pip requirements files')

    args = parser.parse_args()

    uid = hash_files(args.files)

    path = os.path.join(os.getcwd(), '.curds')

    settings = {}

    # The user doesn't need anything else, but the hash of the files
    if args.show_hash:
        return print(uid)

    if args.pypi_url:
        settings['index-url'] = args.pypi_url

    # Default command, just curdle!
    manager = CurdManager(path, settings)

    curd = manager.get(uid)
    if not curd:
        print('[info] No cache found')

    if not curd and not args.remote_cache_url:
        print('[info] No external cache informed, using pip to curdle')
    elif not curd:
        print('[info] Looking for curds in the given url')
        manager.settings.update({'cache-url': args.remote_cache_url})
        curd = manager.retrieve(uid)

    if not curd:
        print('[info] Curdling')
        curd = manager.new(args.files)

    if args.server:
        # Spawning the server!
        host, port = args.server.split(':')
        Server(manager, __name__).run(debug=True, host=host, port=int(port))
    else:
        # Installing the curdled dependencies
        print('[info] Installing curdled packages')
        manager.install(args.files)


if __name__ == '__main__':
    # Module interface, you can use this function by calling this module using
    # the module launcher of python: `python -m milieu`
    main()
