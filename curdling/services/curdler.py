from __future__ import absolute_import, print_function, unicode_literals
from ..exceptions import UnpackingError, BuildError, NoSetupScriptFound
from ..util import spaces
from .base import Service

import os
import re
import sys
import subprocess
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
    with open(filename) as f:
        file_start = f.read(SUPPORTED_FORMATS_MAX_LEN)
    for magic, filetype in SUPPORTED_FORMATS.items():
        if file_start.startswith(magic):
            return filetype
    raise UnpackingError('Unknown compress format for file %s' % filename)


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
        args = [PYTHON_EXECUTABLE]
        args.append('-c')
        args.append(
            r"import setuptools;__file__=%r;"
            r"exec(compile(open(__file__).read().replace('\r\n', '\n'), __file__, 'exec'))" % script)
        args.append(command)
        args.extend(custom_args)

        # Boom! Executing the command.
        builder = subprocess.Popen(args, cwd=cwd,
            stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        _, errs = builder.communicate()
        if builder.returncode != 0:
            raise Exception(errs)

        # Directory where the wheel will be saved after building it, returning
        # the path pointing to the generated file
        output_dir = os.path.join(cwd, 'dist')
        return os.path.join(output_dir, os.listdir(output_dir)[0])


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
        if setup_scripts:
            setup_py = sorted(setup_scripts, key=lambda e: len(e))[0]
            fp.extractall(destination)
        else:
            raise NoSetupScriptFound()
    except ValueError:
        raise NoSetupScriptFound('No setup.py script was found here')
    finally:
        fp.close()
    return Script(os.path.join(destination, setup_py))


class Curdler(Service):

    def handle(self, requester, package, sender_data):
        source = sender_data.pop('path')

        # Place used to unpack the wheel
        destination = tempfile.mkdtemp()

        # Unpackaging the file we just received. The unpack function will give
        # us the path for the setup.py script and building the wheel file with
        # the `bdist_wheel` command.
        try:
            setup_py = unpack(package=source, destination=destination)
            wheel_file = setup_py('bdist_wheel')
            return {'path': self.index.from_file(wheel_file)}
        except BaseException as exc:
            raise BuildError('{0}: {1}'.format(package, spaces(3, str(exc))))
        finally:
            shutil.rmtree(destination)
