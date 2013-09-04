from __future__ import unicode_literals, print_function
from curdling.web import Server

import argparse


def parse_args():
    parser = argparse.ArgumentParser(
        description='Share your cheese binaries with your folks')

    parser.add_argument(
        'curddir', metavar='DIRECTORY',
        help='Path for your cache directory')

    parser.add_argument(
        '-d', '--debug', action='store_true', default=False,
        help='Runs without gevent and enables debug')

    parser.add_argument(
        '-H', '--host', default='0.0.0.0',
        help='Host name to bind')

    parser.add_argument(
        '-p', '--port', type=int, default=8000,
        help='Port to bind')

    return parser.parse_args()


def main():
    server = Server(parse_args())
    server.start()


if __name__ == '__main__':
    main()
