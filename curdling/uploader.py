from __future__ import absolute_import, unicode_literals, print_function
from .service import Service

import os
import urlparse
import requests


class Uploader(Service):

    def handle(self, requester, package, sender_data):
        path = self.index.get("{0};whl".format(package))
        for source in self.sources:
            self.put(path, source)

    def put(self, path, source):
        self.sources = self.conf.get('curdling_urls', [])
        package = os.path.basename(path)
        url = urlparse.urljoin(source, package)
        print(' * uploader:put {0}'.format(url), end='\n')
        with open(path, 'rb') as data:
            requests.put(url, files={package: data}, data={package: package})
