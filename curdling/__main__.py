from __future__ import unicode_literals, print_function
from curdling import hash_files, CurdManager
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
        'files', metavar='FILE', nargs='+',
        help='List of pip requirements files')

    args = parser.parse_args()

    uid = hash_files(args.files)

    path = os.path.join(os.getcwd(), '.curds')

    settings = {}

    # The user doesn't need anything else, but the hash of the files
    if args.show_hash:
        return uid

    if args.pypi_url:
        settings['index-url'] = args.pypi_url

    # Default command, just curdle!
    manager = CurdManager(path, settings)
    output = []

    curd = manager.get(uid)
    if not curd:
        output.append('[info] No cache found')

    if not args.remote_cache_url:
        output.append('[info] No external cache informed, using pip to curdle')

    output.append('[info] Curdling')
    curd = manager.new(args.files)

    # Installing the curdled dependencies
    output.append('[info] Installing curdled packages')
    manager.install(args.files)

    return '\n'.join(output)


if __name__ == '__main__':
    # Module interface, you can use this function by calling this module using
    # the module launcher of python: `python -m milieu`
    print(main() or '')
