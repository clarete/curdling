# Curdling - Concurrent package manager for Python
#
# Copyright (C) 2013-2014  Lincoln Clarete <lincoln@clarete.li>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from .version import __version__


class TagBag(dict):
    __setattr__ = dict.__setitem__
    __getattr__ = dict.__getitem__

    @classmethod
    def from_input(cls, value):
        return value \
            if hasattr(value, 'lower') and value.lower() not in ('any', 'none') \
            else None


class Wheel(object):

    def __init__(self):
        self.distribution = None
        self.version = None
        self.build = None
        self.tags = TagBag()

    @classmethod
    def from_name(cls, name):
        name = name.replace('.whl', '')
        pieces = name.split('-')
        offset = 6 - len(pieces)

        instance = cls()
        instance.distribution = pieces[0]
        instance.version = pieces[1]
        instance.build = pieces[2] if not offset else None
        instance.tags.pyver = pieces[3 - offset]
        instance.tags.abi = TagBag.from_input(pieces[4 - offset])
        instance.tags.arch = TagBag.from_input(pieces[5 - offset])
        return instance

    def name(self):
        return '-'.join((
            self.distribution,
            self.version,
            self.build,
            self.tags.pyver,
            self.tags.abi or 'none',
            self.tags.arch or 'any',
        ))

    def expand_tags(self):
        return ['-'.join([
            pyver,
            self.tags.abi or 'none',
            self.tags.arch or 'any',
        ]) for pyver in self.tags.pyver.split('.')]

    def info(self):
        return {
            'Wheel-Version': '1.0',  # Shamelessly hardcoded
            'Generator': 'Curdling {0}'.format(__version__),
            'Root-Is-Purelib': 'True',
            'Build': self.build,
            'Tag': self.expand_tags(),
        }
