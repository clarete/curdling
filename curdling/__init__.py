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


class CurdManager(object):
    def __init__(self, settings):
        self.settings = settings

    def get(self, path, uid):
        return Curd(path, uid)

    def new(self, path, requirements):
        uid = hash_files(requirements)
        params = {
            'wheel_dir': os.path.join(path, uid),
        }

        if 'index-url' in self.settings:
            params.update({'index_url': self.settings['index-url']})

        for reqfile in requirements:
            params.update({'r': reqfile})
            pip.wheel(**params)
        return self.get(path, uid)


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
