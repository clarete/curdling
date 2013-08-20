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
    def __init__(self, settings=None):
        self.settings = (settings or {})

    def get(self, path, uid):
        return (os.path.exists(os.path.join(path, uid))
                and Curd(path, uid)
                or None)

    def new(self, path, requirements):
        uid = hash_files(requirements)

        # Trying to use the cache
        curd = self.get(path, uid)
        if curd:
            return curd

        # No cached curd, let's move on and build our own
        params = {
            'wheel_dir': os.path.join(path, uid),
        }

        if 'index-url' in self.settings:
            params.update({'index_url': self.settings['index-url']})

        # Iterating over all the requirement files we have here
        for reqfile in requirements:
            params.update({'r': reqfile})
            pip.wheel(**params)

        return self.get(path, uid)


class Curd(object):
    def __init__(self, path, uid):
        self.path = os.path.join(path, uid)
        self.uid = uid

    @property
    def created(self):
        return datetime.fromtimestamp(
            os.stat(self.path).st_ctime)

    def __eq__(self, other):
        return self.path == other.path
