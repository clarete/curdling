from __future__ import absolute_import, print_function, unicode_literals

from . import exceptions
from .database import Database
from .util import logger, parse_requirement


class Uninstall(object):

    def __init__(self, conf):
        self.conf = conf
        self.packages = []
        self.logger = logger(__name__)

    def report(self):
        pass

    def request_uninstall(self, requirement):
        self.packages.append(parse_requirement(requirement).name)

    def run(self):
        for package in self.packages:
            self.logger.info("Removing package %s", package)

            try:
                Database.uninstall(package)
            except exceptions.PackageNotInstalled:
                self.logger.error("Package %s does not exist, skipping", package)
