from __future__ import absolute_import, print_function, unicode_literals
from functools import wraps
from collections import defaultdict

from .database import Database
from .index import PackageNotFound
from .maestro import Maestro
from .signal import SignalEmitter, Signal
from .util import logger, is_url, parse_requirement, safe_name
from .exceptions import VersionConflict

from .services.downloader import Finder, Downloader
from .services.curdler import Curdler
from .services.dependencer import Dependencer
from .services.installer import Installer
from .services.uploader import Uploader

import os
import time


PACKAGE_BLACKLIST = (
    'setuptools',
)


def only(func, field):
    @wraps(func)
    def wrapper(requester, **data):
        if data.get(field, False):
            return func(requester, **data)
    return wrapper


class Install(SignalEmitter):

    def __init__(self, conf):
        super(Install, self).__init__()

        self.conf = conf
        self.index = self.conf.get('index')
        self.database = Database()
        self.logger = logger(__name__)

        # Used by the CLI tool
        self.update_retrieve_and_build = Signal()
        self.update_install = Signal()
        self.update_upload = Signal()
        self.finished = Signal()

        # General params for all the services
        args = self.conf
        args.update({
            'env': self,
            'index': self.index,
            'conf': self.conf,
            'unique': True,
        })

        self.maestro = Maestro()
        self.requirements = set()
        self.errors = []
        self.stats = defaultdict(int)

        self.finder = Finder(**args)
        self.downloader = Downloader(**args)
        self.curdler = Curdler(**args)
        self.dependencer = Dependencer(**args)
        self.installer = Installer(**args)
        self.uploader = Uploader(**args)

    def pipeline(self):
        # Building the pipeline to [find -> download -> build -> find deps]
        self.finder.connect('finished', self.downloader.queue)
        self.downloader.connect('finished', only(self.curdler.queue, 'tarball'))
        self.downloader.connect('finished', only(self.dependencer.queue, 'wheel'))
        self.curdler.connect('finished', self.dependencer.queue)
        self.dependencer.connect('dependency_found', self.feed)

        # Error report, let's just remember what happened
        def update_error_list(name, **data):
            for field, value in list(data.items()):
                self.maestro.set_data(safe_name(data['requirement']), field, value)
            self.errors.append(data)

        # Count how many packages we have in each place
        def update_count(name, **data):
            self.stats[name] += 1
            for field, value in list(data.items()):
                self.maestro.set_data(safe_name(data['requirement']), field, value)

        [(s.connect('finished', update_count),
          s.connect('failed', update_error_list)) for s in [
            self.finder, self.downloader, self.curdler,
            self.dependencer, self.installer, self.uploader,
        ]]

    def count(self, service):
        return self.stats[service]

    def start(self):
        self.finder.start()
        self.downloader.start()
        self.curdler.start()
        self.dependencer.start()

    def set_url(self, data):
        requirement = data['requirement']
        if is_url(requirement):
            data['url'] = requirement
            return True
        return False

    def set_tarball(self, data):
        try:
            data['tarball'] = \
                self.index.get("{0};~whl".format(data['requirement']))
            return True
        except PackageNotFound:
            return False

    def set_wheel(self, data):
        try:
            data['wheel'] = \
                self.index.get("{0};whl".format(data['requirement']))
            return True
        except PackageNotFound:
            return False

    def feed(self, requester, **data):
        requirement = safe_name(data['requirement'])

        # Blacklist
        if safe_name(parse_requirement(requirement).name) in PACKAGE_BLACKLIST:
            return

        # Filter duplicated requirements
        if safe_name(requirement) in self.requirements:
            return
        self.requirements.add(requirement)

        # Defining which place we're moving our requirements
        service = self.finder
        if self.set_wheel(data):
            service = self.dependencer
        elif self.set_tarball(data):
            service = self.curdler
        elif self.set_url(data):
            service = self.downloader

        # Registering information in maestro
        self.maestro.file_requirement(
            requirement,
            dependency_of=data.get('dependency_of'))
        for field, value in list(data.items()):
            self.maestro.set_data(requirement, field, value)

        # Finally feeding the chosen service
        service.queue(requester, **data)

    def load_installer(self):
        errors = defaultdict(list)
        package_names = set(parse_requirement(r).name for r in self.requirements)
        for package_name in package_names:
            try:
                _, chosen_requirement = self.maestro.best_version(package_name)
            except Exception as exc:
                for requirement in self.maestro.get_requirements_by_package_name(package_name):
                    exception = self.maestro.get_data(requirement, 'exception') or exc
                    dependency_of = self.maestro.mapping[requirement]['dependency_of']
                    errors[package_name].append({
                        'exception': exception,
                        'requirement': requirement,
                        'dependency_of': dependency_of,
                    })
            else:
                wheel = self.maestro.get_data(chosen_requirement, 'wheel')
                self.installer.queue('main',
                    requirement=chosen_requirement, wheel=wheel)
        return package_names, errors

    def retrieve_and_build(self):
        # Wait until all the packages have the chance to be processed
        while True:
            total = len(self.requirements)
            retrieved = self.count('downloader')
            built = self.count('dependencer')
            failed = len(self.errors)
            self.emit('update_retrieve_and_build',
                total, retrieved, built, failed)
            if total == built + failed:
                break
            time.sleep(0.5)

        # Walk through all the requested requirements and queue their best
        # version
        packages, errors = self.load_installer()
        if errors:
            self.emit('finished', errors)
            return []
        return packages

    def install(self, packages):
        self.installer.start()
        while True:
            total = len(packages)
            installed = self.count('installer')
            self.emit('update_install', total, installed)
            if total == installed:
                break
            time.sleep(0.5)

    def load_uploader(self):
        failures = self.finder.get_servers_to_update()
        total = sum(len(v) for v in failures.values())
        if not total:
            return total

        self.uploader.start()
        for server, package_names in failures.items():
            for package_name in package_names:
                try:
                    _, requirement = self.maestro.best_version(package_name)
                except VersionConflict:
                    continue
                wheel = self.maestro.get_data(requirement, 'wheel')
                self.uploader.queue('main',
                    wheel=wheel, server=server, requirement=requirement)
        return total

    def upload(self):
        total = self.load_uploader()
        while total:
            uploaded = self.count('uploader')
            self.emit('update_upload', total, uploaded)
            if total == uploaded:
                break
            time.sleep(0.5)

    def run(self):
        packages = self.retrieve_and_build()
        if packages:
            self.install(packages)
        if not self.errors and self.conf.get('upload'):
            self.upload()
        return self.emit('finished')
