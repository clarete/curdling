from __future__ import unicode_literals, print_function
from curdling import curdle, hash_files
import argparse


def main():
    parser = argparse.ArgumentParser(
        description='Curdles your cheesy code and extracts its binaries')
    parser.add_argument(
        '-H', '--show-hash', action='store_true',
        help='Shows the SHA1 hash of a list of concatenated files')
    parser.add_argument(
        'files', metavar='FILE', nargs='+',
        help='List of pip requirements files')

    args = parser.parse_args()

    if args.show_hash:
        return hash_files(args.files)

    return curdle(args.files)


if __name__ == '__main__':
    # Module interface, you can use this function by calling this module using
    # the module launcher of python: `python -m milieu`
    print(main() or '')
