from __future__ import absolute_import, print_function, unicode_literals
from ..exceptions import UnpackingError, BuildError, NoSetupScriptFound
from ..util import execute_command
from .base import Service

import io
import fnmatch
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
SUPPORTED_FORMATS_MAX_LEN = (max(len(x) for x in SUPPORTED_FORMATS) + 7) & ~7

# Matcher for egg-info directories
EGG_INFO_RE = re.compile(r'(-py\d\.\d)?\.egg-info', re.I)


def guess_file_type(filename):
    with io.open(filename, 'rb') as f:
        file_start = f.read(SUPPORTED_FORMATS_MAX_LEN)
    for magic, filetype in SUPPORTED_FORMATS.items():
        if file_start.startswith(magic):
            return filetype
    raise UnpackingError('Unknown compress format for file %s' % filename)


def unpack(package):
    file_type = guess_file_type(package)

    # The only extensions we currently support are `zip', `gz' and `bz2'
    if file_type in ('gz', 'bz2'):
        fp = tarfile.open(package, 'r')
        return fp, [x.name for x in fp.getmembers()]
    if file_type == 'zip':
        fp = zipfile.ZipFile(package)
        return fp, fp.namelist()
    raise UnpackingError('Unknown compress format for file %s' % package)


def find_setup_script(names):
    setup_scripts = [x for x in names if x[-8:] == 'setup.py']
    if not setup_scripts:
        raise NoSetupScriptFound('No setup.py script found')
    return sorted(setup_scripts, key=lambda e: len(e))[0]


def get_setup_from_package(package, destination):
    fp, namelist = unpack(package=package)
    try:
        setup_py = find_setup_script(namelist)
        fp.extractall(destination)
    finally:
        fp.close()
    return os.path.join(destination, setup_py)


def run_setup_script(path, command, *custom_args):
    # What we're gonna run
    cwd = os.path.dirname(path)
    script = os.path.basename(path)

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
    wheel = fnmatch.filter(os.listdir(output_dir), "*.whl")[0]
    return os.path.join(output_dir, wheel)


class Curdler(Service):

    def handle(self, requester, data):
        requirement = data['requirement']
        tarball = data.get('tarball')
        directory = data.get('directory')

        # Place used to unpack the wheel
        destination = tempfile.mkdtemp()

        # Unpackaging the file we just received. The unpack function will give
        # us the path for the setup.py script and building the wheel file with
        # the `bdist_wheel` command.
        try:
            #  may raise NoSetupScriptFound
            setup_py = (os.path.join(directory, 'setup.py') \
                if directory
                else get_setup_from_package(tarball, destination))
            wheel_file = run_setup_script(setup_py, 'bdist_wheel')
            return {
                'wheel': self.index.from_file(wheel_file),
                'requirement': requirement
            }
        except BaseException as exc:
            raise BuildError(str(exc))
        finally:
            shutil.rmtree(destination)

            # This folder was created by the downloader and it's a temporary
            # resource that we don't need anymore.
            if directory:
                shutil.rmtree(directory)
