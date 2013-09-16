from __future__ import absolute_import, unicode_literals, print_function
from .service import Service

import io
import os
import urllib3
import urlparse


class Uploader(Service):

    def __init__(self, *args, **kwargs):
        super(Uploader, self).__init__(*args, **kwargs)
        self.opener = urllib3.PoolManager()

    def handle(self, requester, package, sender_data):
        # Preparing the url to PUT the file
        path = sender_data.pop('path')
        server = sender_data.pop('server')
        package = os.path.basename(path)
        url = urlparse.urljoin(server, 'p/{0}'.format(package))

        # Sending the file to the server. Both `method` and `url` parameters
        # for calling `request_encode_body()` must be `str()` instances, not
        # unicode.
        contents = io.open(path, 'rb').read()
        self.opener.request_encode_body(
            b'PUT', bytes(url), {package: (package, contents)})
        return {'url': url}
