from __future__ import absolute_import, print_function, unicode_literals
from distlib.util import parse_requirement

from . import exceptions
from .database import Database
from .logging import Logger
from .util import safe_name


class Uninstall(object):

    def __init__(self, conf):
        self.conf = conf
        self.logger = Logger('uninstall', conf.get('log_level'))
        self.packages = []

    def report(self):
        pass

    def request_uninstall(self, package):
        self.packages.append(safe_name(parse_requirement(package).name))

    def run(self):
        for package in self.packages:
            self.logger.level(2, "Removing package %s", package)

            try:
                Database.uninstall(package)
            except exceptions.PackageNotInstalled:
                self.logger.level(1, "Package %s does not exist, skipping", package)
