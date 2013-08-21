import os
import tarfile
from StringIO import StringIO
from json import dumps
from flask import Flask, url_for


class Server(Flask):
    def __init__(self, manager, *args, **kwargs):
        super(Server, self).__init__(*args, **kwargs)
        self.initialize_urls()
        self.manager = manager

    def initialize_urls(self):
        self.add_url_rule('/', 'index', self.index)
        self.add_url_rule('/<uid>', 'curd', self.curd)

    def index(self):
        return dumps([{
            'uid': c.uid,
            'url': url_for('curd', uid=c.uid),
        } for c in self.manager.available()])

    def curd(self, uid):
        fobj = StringIO()
        tar = tarfile.open(
            name='{}.tar'.format(uid),
            mode='w',
            fileobj=fobj,
        )

        curd = self.manager.get(uid)
        for wheel in curd.members():
            tar.add(os.path.join(curd.path, wheel), arcname=wheel)

        tar.close()
        fobj.seek(0)

        response = self.make_response(fobj.read())
        response.mimetype = 'application/tar'
        return response
