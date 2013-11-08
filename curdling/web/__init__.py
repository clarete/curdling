from __future__ import unicode_literals, print_function, absolute_import

from flask import Flask, render_template, send_file, request, Response
from flask import Blueprint, current_app, url_for
from gevent.pywsgi import WSGIServer
from functools import wraps

from ..index import Index, PackageNotFound

import os
import json
import crypt


class HtPasswd(object):

    def __init__(self, path):
        self.path = path
        self.users = self.load()

    def enabled(self):
        return self.path is not None

    def auth(self, username, clear_password):
        try:
            crypted_passwd = self.users[username]
        except KeyError:
            return False
        return crypt.crypt(clear_password, crypted_passwd) == crypted_passwd

    def load(self):
        users = {}
        if not self.enabled():
            return users

        with open(self.path) as fd:
            for line in fd.read().splitlines():
                line = line.split('#')[0].strip()
                if line:
                    username, password = line.split(':', 1)
                    users[username] = password
        return users


class Authenticator(object):
    def __init__(self, user_db):
        self.db = HtPasswd(user_db)

    def authenticate(self):
        """Sends a 401 response that enables the basic auth"""
        return Response(
            'Could not verify your account info before processing that URL.\n'
            'You have to login with proper credentials', 401, {
                'WWW-Authenticate': 'Basic realm="Login Required"'
            })

    def __call__(self, f):
        @wraps(f)
        def decorated(*args, **kwargs):
            # If the user didn't provide a user database file we won't ask for
            # authentication here
            if not self.db.enabled():
                return f(*args, **kwargs)

            # Let's just authenticate the user, returning the actual view on
            # success or the `self.authenticate()` result otherwise
            auth = request.authorization
            if not auth or not self.db.auth(auth.username, auth.password):
                return self.authenticate()
            return f(*args, **kwargs)
        return decorated



class API(Blueprint):
    def __init__(self, user_db):
        super(API, self).__init__('api', __name__)

        # Building the authenticator
        auth = Authenticator(user_db)
        self.add_url_rule('/', 'index', auth(self.web_index))
        self.add_url_rule('/<package>', 'package', auth(self.web_package))

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


class App(Flask):

    def __init__(self, index, user_db=None):
        super(App, self).__init__(__name__)

        self.index = index

        auth = Authenticator(user_db)

        self.register_blueprint(API(user_db), url_prefix='/api')
        self.add_url_rule('/', 'index', auth(self.web_index))
        self.add_url_rule('/s/<query>', 'search', auth(self.web_search))
        self.add_url_rule('/p/<package>', 'download', auth(self.web_download))
        self.add_url_rule('/p/<package>', 'upload', auth(self.web_upload),
                          methods=['PUT'])

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


class Server(object):

    def __init__(self, curddir, user_db):
        index = Index(curddir)
        index.scan()

        self.app = App(index, user_db)

    def start(self, host='0.0.0.0', port=8000, debug=False):
        if debug:
            self.app.run(host=host, port=port, debug=True)
        else:
            WSGIServer((host, port), self.app).serve_forever()
