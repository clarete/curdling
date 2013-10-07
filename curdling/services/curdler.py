from __future__ import absolute_import, print_function, unicode_literals
from ..exceptions import UnpackingError, BuildError, NoSetupScriptFound
from ..util import execute_command
from .base import Service

from ..vendor.wheel.egg2wheel import egg2wheel

import io
import os
import re
import sys
import shutil
import tempfile
import zipfile
import tarfile


# We'll use it to call the `setup.py` script of packages we're building
PYTHON_EXECUTABLE = sys.executable.encode(sys.getfilesystemencoding())

# Those are the formats we know how to extract, if you need to add a new one
# here, please refer to the page[0] to check the magic bits of the file type
# you wanna add.
#
# [0] http://www.garykessler.net/library/file_sigs.html
SUPPORTED_FORMATS = {
    b"\x1f\x8b\x08": "gz",
    b"\x42\x5a\x68": "bz2",
    b"\x50\x4b\x03\x04": "zip"
}

# Must be greater than the length of the biggest key of `SUPPORTED_FORMATS`, to
# be used as the block size to `file.read()` in `guess_file_type()`
SUPPORTED_FORMATS_MAX_LEN = max(len(x) for x in SUPPORTED_FORMATS)

# Matcher for egg-info directories
EGG_INFO_RE = re.compile(r'(-py\d\.\d)?\.egg-info', re.I)


def get_paths(directory='', check=False):
    paths = {}
    for sub in "purelib", "platlib", "headers", "data":
        path = os.path.join(directory, sub)
        if not check or os.path.exists(path):
            paths[sub] = path
    return paths


def guess_file_type(filename):
    with io.open(filename, 'rb') as f:
        file_start = f.read(SUPPORTED_FORMATS_MAX_LEN)
    for magic, filetype in SUPPORTED_FORMATS.items():
        if file_start.startswith(magic):
            return filetype
    raise UnpackingError('Unknown compress format for file %s' % filename)


def first_in_directory(path):
    return os.path.join(path, os.listdir(path)[0])


class Script(object):

    def __init__(self, path):
        self.path = path

    def __call__(self, command, *custom_args):
        # What we're gonna run
        cwd = os.path.dirname(self.path)
        script = os.path.basename(self.path)

        # Building the argument list starting from the interpreter path. This
        # weird we're doing here was copied from `pip` and it basically forces
        # the usage of setuptools instead of distutils or any other weird
        # library people might be using.
        args = ['-c']
        args.append(
            r"import setuptools;__file__=%r;"
            r"exec(compile(open(__file__).read().replace('\r\n', '\n'), __file__, 'exec'))" % script)
        args.append(command)
        args.extend(custom_args)

        # Boom! Executing the command.
        execute_command(PYTHON_EXECUTABLE, *args, cwd=cwd)

        # Directory where the wheel will be saved after building it, returning
        # the path pointing to the generated file
        output_dir = os.path.join(cwd, 'dist')
        return first_in_directory(output_dir)


def unpack(package, destination):
    file_type = guess_file_type(package)

    # The only extensions we support currently
    if file_type == 'zip':
        fp = zipfile.ZipFile(package)
        get_names = fp.namelist
    elif file_type in ('gz', 'bz2'):
        fp = tarfile.open(package, 'r')
        get_names = lambda: [x.name for x in fp.getmembers()]

    # Find the setup.py script among the other contents
    try:
        setup_scripts = [x for x in get_names() if x.endswith('setup.py')]
        if not setup_scripts:
            raise ValueError
        else:
            setup_py = sorted(setup_scripts, key=lambda e: len(e))[0]
            fp.extractall(destination)
    except ValueError:
        msg = 'No setup.py script was found in `{0}\''.format(
            os.path.basename(package))
        raise NoSetupScriptFound(msg)
    finally:
        fp.close()
    return Script(os.path.join(destination, setup_py))


class Curdler(Service):

    def handle(self, requester, requirement, sender_data):
        source = sender_data.get('path')
        wheel_directory = tempfile.mkdtemp()
        unpack_directory = tempfile.mkdtemp()

        try:
            # The build process is separated in a few steps. Finding the
            # setup.py script is the first one. It might come either from a
            # folder or from a compressed file.
            if os.path.isdir(source):
                setup_py = Script(os.path.join(source, 'setup.py'))
            else:
                setup_py = unpack(package=source, destination=unpack_directory)

            # The second step is actually executing the setup.py script. The
            # easiest way to generate the wheel would be using `bdist_wheel`.
            # We're not doing that here cause our `wheel` package is vendorized
            # so its entry points are not available.
            egg2wheel(setup_py('bdist_egg'), wheel_directory)
            return {'path': self.index.from_file(
                first_in_directory(wheel_directory))}

        # except BaseException as exc:
        #     raise BuildError(str(exc))

        finally:
            shutil.rmtree(wheel_directory)
            shutil.rmtree(unpack_directory)

            # This folder was created by the downloader and it's a temporary
            # resource that we don't need anymore.
            if os.path.isdir(source):
                shutil.rmtree(source)
