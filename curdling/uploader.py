from __future__ import absolute_import, unicode_literals, print_function
from .service import Service

import os
import urlparse
import requests


class Uploader(Service):

    def handle(self, requester, package, sender_data):
        path = sender_data.pop('path')
        server = sender_data.pop('server')
        package = os.path.basename(path)
        url = urlparse.urljoin(server, 'p/{0}'.format(package))
        with open(path, 'rb') as data:
            requests.put(url, files={package: data}, data={package: package})
        return {'url': url}
