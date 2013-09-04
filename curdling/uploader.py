from __future__ import absolute_import, unicode_literals, print_function
from .service import Service

import os
import urlparse
import requests


class Uploader(Service):
    def __init__(self, sources, *args, **kwargs):
        self.sources = sources
        self.index = kwargs.pop('index')
        super(Uploader, self).__init__(
            callback=self.upload,
            *args, **kwargs)


    def put(self, path, source):
        # Getting the wheel we're going to send
        package = os.path.basename(path)
        url = urlparse.urljoin(source, package)
        print(' * uploader:put {0}'.format(url), end='\n')
        with open(path, 'rb') as data:
            requests.put(url, files={package: data}, data={package: package})


    def upload(self, package):
        path = self.index.get("{0};whl".format(package))
        for source in self.sources:
            self.put(path, source)
