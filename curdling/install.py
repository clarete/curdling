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
from distlib.compat import queue

from .database import Database
from .index import PackageNotFound
from .mapping import Mapping
from .signal import SignalEmitter, Signal
from .util import logger, is_url, parse_requirement, safe_name
from .exceptions import VersionConflict

from .services.base import Service
from .services.downloader import Finder, Downloader
from .services.curdler import Curdler
from .services.dependencer import Dependencer
from .services.installer import Installer
from .services.uploader import Uploader

import os
import sys
import time
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


class Install(Service):

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

        # Track dependencies and requirements to be installed
        self.mapping = Mapping()

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
        self.dependencer.connect('dependency_found', self.queue)

        # Save the wheels that reached the end of the flow
        def queue_install(requester, **data):
            self.mapping.wheels[data['requirement']] = data['wheel']
        self.dependencer.connect('finished', queue_install)

        # Error report, let's just remember what happened
        def update_error_list(name, **data):
            package_name = parse_requirement(data['requirement']).name
            self.mapping.errors[package_name][data['requirement']] = {
                'exception': data['exception'],
                'dependency_of': [data.get('dependency_of')],
            }

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

    def handle(self, requester, **data):
        requirement = safe_name(data['requirement'])
        if not is_url(requirement) and parse_requirement(requirement).name in PACKAGE_BLACKLIST:
            return

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
        errors = defaultdict(dict)
        installable_packages = self.mapping.installable_packages()
        for package_name in installable_packages:
            try:
                _, chosen_requirement = self.mapping.best_version(package_name)
            except Exception as exc:
                self.logger.exception("best_version('%s'): %s:%d (%s) %s",
                    package_name, *traceback.extract_tb(sys.exc_info()[2])[0])
                for requirement in self.mapping.get_requirements_by_package_name(package_name):
                    previous_error = self.mapping.errors[package_name].get(requirement)
                    exception = previous_error['exception'] if previous_error else exc
                    errors[package_name][requirement] = {
                        'exception': exception,
                        'dependency_of': self.mapping.dependencies[requirement],
                    }
            else:
                # It's OK to queue each package without being sure
                # about the availability of all the requirements. The
                # Installer service will not be started until everything
                # is checked.
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
            # Walking over the whole list of requirements to
            # process.
            while True:
                try:
                    requester, sender_data = self._queue.get_nowait()
                    self.handle(requester, **sender_data)
                except queue.Empty:
                    break

            # No more requirements to process, let's take a look in
            # the current situation and see if we're finally ready to
            # bail out.
            total = len(self.mapping.requirements)
            retrieved = self.mapping.count('downloader') + len(self.mapping.repeated)
            built = self.mapping.count('dependencer')

            # Each package might have more than one requirement
            failed = sum(len(x) for x in self.mapping.errors.values())
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
            failed = sum(len(x) for x in self.mapping.errors.values())
            self.emit('update_install', total, installed, failed)
            if total == installed + failed:
                break
            time.sleep(0.5)

        # Signaling failures that happened during the installation
        if self.mapping.errors:
            self.emit('finished', self.mapping.errors)
            return []

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
        if packages:
            self.install(packages)
        if not self.mapping.errors and self.conf.get('upload'):
            self.upload()
        return self.emit('finished')
