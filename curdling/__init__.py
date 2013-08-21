import io
import os
import hashlib
import urllib2
import urlparse
import tarfile
from StringIO import StringIO
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
    def __init__(self, path, settings=None):
        self.path = path
        self.settings = (settings or {})

        # Saves the mapping of uids to files
        self.mapping = {}

        # Installs the curd directory if it does not exist
        self.install_folder()

    def install_folder(self):
        # Just making sure the target directory exists
        os.path.isdir(self.path) or os.makedirs(self.path)

    def add(self, requirements):
        uid = hash_files(requirements)
        self.mapping[uid] = requirements
        return uid

    def get(self, uid):
        return (os.path.exists(os.path.join(self.path, uid))
                and Curd(self.path, uid)
                or None)

    def new(self, uid):
        # Trying to use the cache
        curd = self.get(uid)
        if curd:
            return curd

        # No cached curd, let's move on and build our own
        params = {
            'wheel_dir': os.path.join(self.path, uid),
        }

        if 'index-url' in self.settings:
            params.update({'index_url': self.settings['index-url']})

        if 'extra-index-url' in self.settings:
            params.update({'extra_index_url': self.settings['extra-index-url']})

        # Iterating over all the requirement files we have here
        for reqfile in self.mapping[uid]:
            params.update({'r': reqfile})
            pip.wheel(**params)

        return self.get(uid)

    def install(self, uid):
        params = {
            'use_wheel': True,
            'no_index': True,
            'find_links': os.path.join(self.path, uid),
        }

        for reqfile in self.mapping[uid]:
            params.update({'r': reqfile})
            pip.install(**params)

    def available(self):
        return (os.path.isdir(self.path)
                and [Curd(self.path, cid) for cid in os.listdir(self.path)]
                or [])

    def retrieve(self, uid):
        # Making sure our target directory exists
        path = os.path.join(self.path, uid)
        os.mkdir(path)

        # Retrieving the tar file
        url = urlparse.urljoin(self.settings['cache-url'], uid)
        response = urllib2.urlopen(url)
        tarcontent = response.read()

        # Opening the tar StringIO'ed content. Bad things might happen here if
        # the data does not represent a valid tar file
        tar = tarfile.open(
            name='{}.tar'.format(uid),
            mode='r',
            fileobj=StringIO(tarcontent),
        )

        # Extracting each file to our target directory
        for entry in tar:
            tar.extract(entry, path=path)

        tar.close()
        return self.get(uid)


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

    def members(self):
        return os.listdir(self.path)
