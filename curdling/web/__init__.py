from __future__ import unicode_literals, print_function, absolute_import
from gevent.queue import JoinableQueue
from gevent.pywsgi import WSGIServer
from flask import (
    Flask, Blueprint, render_template, send_file, request, current_app,
)

import os
import json

from ..index import Index, PackageNotFound


api = Blueprint('api', __name__)


@api.route('/')
def api_index():
    return json.dumps(current_app.index.list_packages())


class Server(object):
    def __init__(self, args):
        self.args = args
        self.index = Index(args.curddir)
        self.index.scan()

        self.app = Flask(__name__)
        self.app.index = self.index
        self.app.register_blueprint(api, url_prefix='/api')
        self.app.add_url_rule('/', 'index', self.web_index)
        self.app.add_url_rule('/s/<query>', 'search', self.web_search)
        self.app.add_url_rule('/p/<package>', 'upload', self.web_upload,
                              methods=('PUT',))

    def start(self):
        if self.args.debug:
            self.app.run(host=self.args.host, port=self.args.port, debug=True)
        else:
            WSGIServer((self.args.host, self.args.port), self.app).serve_forever()

    def web_index(self):
        return render_template('index.html', index=self.index)

    def web_search(self, query):
        try:
            path = self.index.get(query)
        except PackageNotFound:
            return 'package not found', 404
        except ValueError:
            return 'your query is wrong', 400
        return send_file(
            path, as_attachment=True,
            attachment_filename=os.path.basename(path))

    def web_upload(self, package):
        """
         * Smart enough to not save things we already have
         * Idempotent, you can call as many times as you need
         * The caller names the package (its basename)
        """
        pkg = request.files[package]
        self.index.from_data(package, pkg.read())
        return 'ok'
