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

import ast
import os
import re
from setuptools import setup, find_packages


class VersionFinder(ast.NodeVisitor):

    def __init__(self):
        self.version = None

    def visit_Assign(self, node):
        if node.targets[0].id == '__version__':
            self.version = node.value.s


def read_version():
    """Read version from curdling/version.py without loading any files"""
    finder = VersionFinder()
    finder.visit(ast.parse(local_file('curdling', 'version.py')))
    return finder.version


def parse_requirements(path):
    """Rudimentary parser for the `requirements.txt` file

    We just want to separate regular packages from links to pass them to the
    `install_requires` and `dependency_links` params of the `setup()`
    function properly.
    """
    try:
        requirements = map(str.strip, local_file(path).splitlines())
    except IOError:
        raise RuntimeError("Couldn't find the `requirements.txt' file :(")

    links = []
    pkgs = []
    for req in requirements:
        if not req:
            continue
        if 'http:' in req or 'https:' in req:
            links.append(req)
            name, version = re.findall("\#egg=([^\-]+)-(.+$)", req)[0]
            pkgs.append('{0}=={1}'.format(name, version))
        else:
            pkgs.append(req)

    return pkgs, links


local_file = lambda *f: \
    open(os.path.join(os.path.dirname(__file__), *f)).read()


install_requires, dependency_links = \
    parse_requirements('requirements.txt')


if __name__ == '__main__':
    setup(
        name="curdling",
        version=read_version(),
        description='Concurrent package manager for Python',
        long_description=local_file('README.rst'),
        author='Lincoln Clarete',
        author_email='lincoln@clarete.li',
        url='https://github.com/clarete/curdling',
        packages=find_packages(exclude=['*tests*']),
        install_requires=install_requires,
        dependency_links=dependency_links,
        include_package_data=True,
        entry_points={
            'console_scripts': [
                'curd = curdling.tool:main',
                'curd-server = curdling.web.__main__:main',
            ]
        },
        classifiers=[
            'Topic :: Software Development :: Build Tools',
            'Intended Audience :: Developers',
            'Intended Audience :: System Administrators',
            'Development Status :: 3 - Alpha',
            'Operating System :: OS Independent',
            'Programming Language :: Python',
            'Programming Language :: Python :: 2.6',
            'Programming Language :: Python :: 2.7',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.1',
            'Programming Language :: Python :: 3.2',
            'Programming Language :: Python :: 3.3',
        ],
        extras_require={
            'server': parse_requirements('requirements-server.txt')[0],
        },
    )
