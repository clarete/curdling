import io
import os
import hashlib
from datetime import datetime
from sh import pip


def hash_files(file_list):
    """Hashes the contents of a list of files
    """
    return hashlib.new(
        'sha1',
        ''.join(io.open(f).read() for f in file_list),
    ).hexdigest()


def get_curd(path, uid):
    return Curd(path, uid)


def new_curd(path, requirements):
    uid = hash_files(requirements)
    for reqfile in requirements:
        pip.wheel(wheel_dir=os.path.join(path, uid), r=reqfile)
    return get_curd(path, uid)


class Curd(object):
    def __init__(self, path, uid):
        self.path = path
        self.uid = uid

    @property
    def created(self):
        return datetime.fromtimestamp(
            os.stat(os.path.join(self.path, self.uid)).st_ctime)


def curdle(file_list):
    return hash_files(file_list)
