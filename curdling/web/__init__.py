from __future__ import unicode_literals, print_function, absolute_import
from flask import Flask, render_template, send_file, request, Response
from flask import Blueprint, current_app, url_for
from gevent.pywsgi import WSGIServer

from ..index import Index, PackageNotFound

import os
import json


class API(Blueprint):
    def __init__(self):
        super(API, self).__init__('api', __name__)
        self.add_url_rule('/', 'index', self.web_index)
        self.add_url_rule('/<package>', 'package', self.web_package)

    def web_index(self):
        return json.dumps(current_app.index.list_packages())

    def web_package(self, package):
        releases = []
        fmt = lambda u: url_for('download', package=u, _external=True)
        for release in current_app.index.package_releases(package, fmt):
            releases.append(release)
        if releases:
            return json.dumps(releases)
        else:
            return json.dumps({'status': 'error'}), 404


class Server(object):
    def __init__(self, args):
        self.args = args
        self.index = Index(args.curddir)
        self.index.scan()

        # Setting up the app
        self.app = Flask(__name__)
        self.app.index = self.index

        # Registering urls
        self.app.register_blueprint(API(), url_prefix='/api')
        self.app.add_url_rule('/', 'index', self.web_index)
        self.app.add_url_rule('/s/<query>', 'search', self.web_search)
        self.app.add_url_rule('/p/<package>', 'download', self.web_download)
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

    def web_download(self, package):
        with self.index.open(package) as pkg:
            return pkg.read()

    def web_upload(self, package):
        """
         * Smart enough to not save things we already have
         * Idempotent, you can call as many times as you need
         * The caller names the package (its basename)
        """
        pkg = request.files[package]
        self.index.from_data(package, pkg.read())
        return 'ok'
