from __future__ import absolute_import, print_function, unicode_literals
from .base import Service
from ..util import get_auth_info_from_url
from distlib import compat

import io
import os
import urllib3


class Uploader(Service):

    def __init__(self, *args, **kwargs):
        super(Uploader, self).__init__(*args, **kwargs)
        self.opener = urllib3.PoolManager()

    def handle(self, requester, data):
        # Preparing the url to PUT the file
        wheel = data.get('wheel')
        server = data.get('server')
        file_name = os.path.basename(wheel)
        url = compat.urljoin(server, 'p/{0}'.format(file_name))

        # Sending the file to the server. Both `method` and `url` parameters
        # for calling `request_encode_body()` must be `str()` instances, not
        # unicode.
        contents = io.open(wheel, 'rb').read()
        self.opener.request_encode_body(
            b'PUT', bytes(url), {file_name: (file_name, contents)},
            headers=get_auth_info_from_url(url))
        return {'upload_url': url, 'requirement': data['requirement']}
