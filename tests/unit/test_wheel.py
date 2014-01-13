from curdling.wheel import Wheel
from curdling.version import __version__


def test_from_name():
    "Wheel.from_name() Should return an instance of `Wheel` with all attributes from the received wheel name"

    # Given the following wheel
    file_name = 'curdzz-0.1.2-1x-py27-none-any'

    # When I parse its name
    wheel = Wheel.from_name(file_name)

    # Then I see that a new wheel object was created with the right
    # attributes
    wheel.distribution.should.equal('curdzz')
    wheel.version.should.equal('0.1.2')
    wheel.tags.build.should.equal('1x')
    wheel.tags.pyver.should.equal('py27')
    wheel.tags.abi.should.be.none
    wheel.tags.arch.should.be.none


def test_from_name_with_ext():
    "Wheel.from_name() Should also work if the name has the '.whl' extension"

    # Given the following wheel
    file_name = 'curdzz-0.1.2-1x-py27-none-any.whl'

    # When I parse its name
    wheel = Wheel.from_name(file_name)

    # Then I see that a new wheel object was created with the right
    # attributes
    wheel.distribution.should.equal('curdzz')
    wheel.version.should.equal('0.1.2')
    wheel.tags.build.should.equal('1x')
    wheel.tags.pyver.should.equal('py27')
    wheel.tags.abi.should.be.none
    wheel.tags.arch.should.be.none


def test_from_name_with_ext():
    "Wheel.from_name() Should also expand compressed tags in the file name"

    # Given the following wheel
    file_name = 'curdzz-0.1.2-1x-py27.py33-none-any.whl'

    # When I parse its name
    wheel = Wheel.from_name(file_name)

    # Then I see that a new wheel object was created with the right
    # attributes
    wheel.distribution.should.equal('curdzz')
    wheel.version.should.equal('0.1.2')
    wheel.tags.build.should.equal('1x')
    wheel.tags.pyver.should.equal('py27.py33')
    wheel.tags.abi.should.be.none
    wheel.tags.arch.should.be.none


def test_name():
    "Wheel.name() Should use the attributes associated to the Wheel instance to build a valid wheel file name"

    # Given the following wheel
    wheel = Wheel()
    wheel.distribution = 'curdzz'
    wheel.version = '0.1.2'
    wheel.tags.build = '1'
    wheel.tags.pyver = 'py27'
    wheel.tags.abi = None
    wheel.tags.arch = None

    # Then I see that the tags property was properly filled out as well
    dict(wheel.tags).should.equal({
        'build': '1',
        'pyver': 'py27',
        'abi': None,
        'arch': None,
    })

    # And when I generate the file name; Then I see that it uses all
    # the previously associated metadata
    wheel.name().should.equal('curdzz-0.1.2-1-py27-none-any')


def test_info():

    # Given the following wheel
    wheel = Wheel.from_name('sure-0.1.2-1x-py27.py33-none-any')

    # When I try to access the info related to that wheel
    info = wheel.info()

    # Then I see it matches all the data described in the wheel file
    # name
    info.should.equal({
        'Wheel-Version': '1.0',
        'Generator': 'Curdling {0}'.format(__version__),
        'Root-Is-Purelib': 'True',
        'Build': '1x',
        'Tag': [
            'py27-none-any',
            'py33-none-any',
        ],
    })