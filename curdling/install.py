# Curdling - Concurrent package manager for Python
# Copyright (C) 2013  Lincoln Clarete <lincoln@clarete.li>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import, print_function, unicode_literals
from functools import wraps
from collections import defaultdict

from .database import Database
from .index import PackageNotFound
from .mapping import Mapping
from .signal import SignalEmitter, Signal
from .util import logger, is_url, parse_requirement, safe_name
from .exceptions import VersionConflict

from .services.downloader import Finder, Downloader
from .services.curdler import Curdler
from .services.dependencer import Dependencer
from .services.installer import Installer
from .services.uploader import Uploader

import os
import sys
import time
import threading
import traceback
import math
import multiprocessing


PACKAGE_BLACKLIST = (
    'setuptools',
)


def only(func, field):
    @wraps(func)
    def wrapper(requester, **data):
        if data.get(field, False):
            return func(requester, **data)
    return wrapper


def unique(func, install):
    @wraps(func)
    def wrapper(requester, **data):
        tarball = os.path.basename(data['url'])
        if tarball not in install.downloader.processing_packages:
            return func(requester, **data)
        else:
            install.mapping.repeated.append(data['requirement'])
            install.mapping.requirements.discard(data['requirement'])
    return wrapper


class Install(SignalEmitter):

    def __init__(self, conf):
        super(Install, self).__init__()

        self.conf = conf
        self.index = self.conf.get('index')
        self.database = Database()
        self.logger = logger(__name__)
        self.only_build = self.conf.get('only_build')

        # Used by the CLI tool
        self.update_retrieve_and_build = Signal()
        self.update_install = Signal()
        self.update_upload = Signal()
        self.finished = Signal()

        # Track dependencies and requirements to be installed
        self.mapping = Mapping()
        self.lock = threading.RLock()

        # General params for all the services
        args = self.conf
        args.update({
            'env': self,
            'index': self.index,
            'conf': self.conf,
        })

        cpu_count = multiprocessing.cpu_count()
        p = lambda n: max(int(math.floor((cpu_count / 8.0) * n)), 1)

        self.finder = Finder(size=p(1), **args)
        self.downloader = Downloader(size=p(2), **args)
        self.curdler = Curdler(size=p(4), **args)
        self.dependencer = Dependencer(size=p(1), **args)
        self.installer = Installer(size=cpu_count, **args)
        self.uploader = Uploader(size=cpu_count, **args)

    def pipeline(self):
        # Building the pipeline to [find -> download -> build -> find deps]
        self.finder.connect('finished', unique(self.downloader.queue, self))
        self.downloader.connect('finished', only(self.curdler.queue, 'directory'))
        self.downloader.connect('finished', only(self.curdler.queue, 'tarball'))
        self.downloader.connect('finished', only(self.dependencer.queue, 'wheel'))
        self.curdler.connect('finished', self.dependencer.queue)
        self.dependencer.connect('dependency_found', self.feed)

        # Save the wheels that reached the end of the flow
        def queue_install(requester, **data):
            self.mapping.wheels[data['requirement']] = data['wheel']
        self.dependencer.connect('finished', queue_install)

        # Error report, let's just remember what happened
        def update_error_list(name, **data):
            package_name = parse_requirement(data['requirement']).name
            self.mapping.errors[package_name].append({
                'exception': data['exception'],
                'requirement': data['requirement'],
                'dependency_of': [data.get('dependency_of')],
            })

        # Count how many packages we have in each place
        def update_count(name, **data):
            self.mapping.stats[name] += 1

        [(s.connect('finished', update_count),
          s.connect('failed', update_error_list)) for s in [
            self.finder, self.downloader, self.curdler,
            self.dependencer, self.installer, self.uploader,
        ]]

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
        if not is_url(requirement) and parse_requirement(requirement).name in PACKAGE_BLACKLIST:
            return

        # Well, that's a bad thing. We wouldn't really need a lock if
        # we used the same pattern that we used in the rest of the
        # system, queuing requirements. Going deeper. It happens
        # because we have a few `dependencer` instances running and
        # they might try to write/read from the mapping at the same
        # time. We'll should get rid of that at some point, creating
        # more granular services that are part of the main pipeline.
        with self.lock:
            # Filter duplicated requirements
            if requirement in self.mapping.requirements:
                return
            # Filter previously primarily required packages
            if self.mapping.was_directly_required(requirement):
                return
            # Save the requirement and its requester for later
            self.mapping.requirements.add(requirement)
            self.mapping.dependencies[requirement].append(data.get('dependency_of'))

        # Defining which place we're moving our requirements
        service = self.finder
        if self.set_wheel(data):
            service = self.dependencer
        elif self.set_tarball(data):
            service = self.curdler
        elif self.set_url(data):
            service = self.downloader

        # Finally feeding the chosen service
        service.queue(requester, **data)

    def load_installer(self):
        # Look for the best version collected for each package.
        # Failures will be collected and forwarded to the caller.
        errors = defaultdict(list)
        installable_packages = self.mapping.installable_packages()
        for package_name in installable_packages:
            try:
                _, chosen_requirement = self.mapping.best_version(package_name)
            except Exception as exc:
                self.logger.exception("best_version('%s'): %s:%d (%s) %s",
                    package_name, *traceback.extract_tb(sys.exc_info()[2])[0])
                for requirement in self.mapping.get_requirements_by_package_name(package_name):
                    errors[package_name].append({
                        'requirement': requirement,
                        'exception': self.mapping.errors.get(requirement, exc),
                        'dependency_of': self.mapping.dependencies[requirement],
                    })
            else:
                # It's OK to queue all the packages without being sure
                # about the availability of all the required packages
                # because the installer service is not actually
                # installed. It won't happen until we check for errors.
                self.installer.queue('main',
                    requirement=chosen_requirement,
                    wheel=self.mapping.wheels[chosen_requirement])

        # Check if the number of packages to install is the same as
        # the number of packages initially requested. If it's not
        # true, it means that a few packages could not be built.  We
        # might have valuable information about the possible failures
        # in the `self.errors` dictionary.
        if installable_packages != self.mapping.initially_required_packages():
            errors.update(self.mapping.errors)
        return installable_packages, errors

    def retrieve_and_build(self):
        # Wait until all the packages have the chance to be processed
        while True:
            total = len(self.mapping.requirements)
            retrieved = self.mapping.count('downloader') + len(self.mapping.repeated)
            built = self.mapping.count('dependencer')
            failed = len(self.mapping.errors)
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
            installed = self.mapping.count('installer')
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
                    _, requirement = self.mapping.best_version(package_name)
                except VersionConflict:
                    continue
                wheel = self.mapping.wheels[requirement]
                self.uploader.queue('main',
                    wheel=wheel, server=server, requirement=requirement)
        return total

    def upload(self):
        total = self.load_uploader()
        while total:
            uploaded = self.mapping.count('uploader')
            self.emit('update_upload', total, uploaded)
            if total == uploaded:
                break
            time.sleep(0.5)

    def run(self):
        packages = self.retrieve_and_build()
        if packages and not self.only_build:
            self.install(packages)
        if not self.mapping.errors and self.conf.get('upload'):
            self.upload()
        return self.emit('finished')
