# Curdling - Concurrent package manager for Python
#
# Copyright (C) 2014  Lincoln Clarete <lincoln@clarete.li>
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

from curdling.wheel import Wheel
from . import FIXTURE


def test_read_basic_fields():
    "Wheel.from_file() Should parse a `.whl` archive"

    # Given the wheel present in our file system
    wheel_file = FIXTURE('storage2/gherkin-0.1.0-py27-none-any.whl')

    # When I parse it
    wheel = Wheel.from_file(wheel_file)

    # Then I see that the wheel file was successfully read
    wheel.distribution.should.equal('gherkin')
    wheel.version.should.equal('0.1.0')
    wheel.build.should.be.none
    wheel.tags.pyver.should.equal('py27')
    wheel.tags.abi.should.be.none
    wheel.tags.arch.should.be.none


def test_read_basic_fields():
    """Wheel.from_file() Should parse the WHEEL file of the .whl archive

    The information inside of this file will be used as data source
    for the `Wheel.info()` method.
    """

    # Given the wheel present in our file system
    wheel_file = FIXTURE('storage2/gherkin-0.1.0-py27-none-any.whl')

    # When I parse it
    wheel = Wheel.from_file(wheel_file)

    # Then I see that
    # And then I also see that the file WHEEL was correctly parsed
    wheel.info().should.equal({
        'Wheel-Version': '1.0',
        'Generator': 'bdist_wheel (0.21.0)',
        'Root-Is-Purelib': 'true',
        'Tag': ['py27-none-any'],
    })

    # # Then I see it should contain the follo
    # files = {
    #     '/', ['blah.py']
    #     'dist-info': [
    #         'DESCRIPTION.rst',
    #         'pydist.json',
    #         'top_level.txt',
    #         'WHEEL',
    #         'METADATA',
    #         'RECORD',
    #     ]
    # }
