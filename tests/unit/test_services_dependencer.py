from mock import call, patch, Mock
from curdling.services.dependencer import Dependencer


@patch('curdling.services.dependencer.Wheel')
def test_dependencer(Wheel):
    "Dependencer#handle() should emit the signal dependency_found when scanning a new package"

    # Given that I have the depencencer service
    callback = Mock()
    dependencer = Dependencer()
    dependencer.connect('dependency_found', callback)

    # And that the package to test the service will have the following
    # dependencies:
    Wheel.return_value = Mock(metadata=Mock(dependencies={
        'install': ['forbiddenfruit (0.1.1)'],
        'extras': {},
    }))

    # When I queue a package and a sentinel and then call the worker
    dependencer.queue('tests', requirement='sure', wheel='forbiddenfruit-0.1-cp27.whl')
    dependencer.queue(None)
    dependencer._worker()

    # Than I see that the signal was called for the dependency with the right
    # parameters
    callback.assert_called_once_with(
        'dependencer',
        requirement='forbiddenfruit (0.1.1)',
        dependency_of='sure')


@patch('curdling.services.dependencer.Wheel')
def test_dependencer_package_with_no_deps(Wheel):
    "Dependencer#handle() should emit the signal built for packages with no dependencies"

    # Given that I have the depencencer service
    callback = Mock()
    dependencer = Dependencer()
    dependencer.connect('finished', callback)

    # And that the package to test the service will have no
    # dependencies:
    Wheel.return_value = Mock(metadata=Mock(dependencies={}))

    # When I queue a package and a sentinel and then call the worker
    dependencer.queue('tests', requirement='sure', wheel='path-to-the-wheel')
    dependencer.queue(None)
    dependencer._worker()

    # Than I see that the signal was called for the dependency with the right
    # parameters
    callback.assert_called_once_with(
        'dependencer',
        requirement='sure',
        wheel='path-to-the-wheel'
    )


@patch('curdling.services.dependencer.Wheel')
def test_dependencer_install_extras(Wheel):
    "Dependencer#handle() Should install extra sets of dependencies"

    # Given that I have the depencencer service
    callback = Mock()
    dependencer = Dependencer()
    dependencer.connect('dependency_found', callback)

    # When I queue a dependency from an extra section the user didn't
    # request
    Wheel.return_value = Mock(metadata=Mock(dependencies={
        'install': ['lxml (>= 2.1)'],
        'extras': {'tests': ['sure (1.2.1)']},
    }))

    # When I queue a package and a sentinel and then call the worker
    dependencer.queue('tests', requirement='curdling[tests]', wheel='path-to-the-wheel')
    dependencer.queue(None)
    dependencer._worker()

    # Then I see no dependencies were actually found, since the extra
    # section doesn't match.
    list(callback.call_args_list).should.equal([
        call('dependencer', requirement=u'lxml (>= 2.1)', dependency_of='curdling[tests]'),
        call('dependencer', requirement=u'sure (1.2.1)', dependency_of='curdling[tests]')
    ])


@patch('curdling.services.dependencer.Wheel')
def test_dependencer_skip_not_required_extras(Wheel):
    "Dependencer#handle() Should skip dependencies from extra sets that the user didn't require"

    # Given that I have the depencencer service
    callback = Mock()
    dependencer = Dependencer()
    dependencer.connect('dependency_found', callback)

    # When I queue a dependency from an extra section the user didn't
    # request
    Wheel.return_value = Mock(metadata=Mock(dependencies={
        'extras': {'development': 'sure'},
    }))

    # When I queue a package and a sentinel and then call the worker
    dependencer.queue('tests', requirement='curdling', wheel='path-to-the-wheel')
    dependencer.queue(None)
    dependencer._worker()

    # Then I see no dependencies were actually found, since the extra
    # section doesn't match.
    callback.called.should.be.false
