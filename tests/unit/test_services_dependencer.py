from mock import Mock, patch
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
    Wheel.return_value = Mock(metadata=Mock(requires_dist=['forbiddenfruit (0.1.1)']))

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

    # And that the package to test the service will have the following
    # dependencies:
    Wheel.return_value = Mock(metadata=Mock(requires_dist=[]))

    # When I queue a package and a sentinel and then call the worker
    dependencer.queue('tests', requirement='sure', wheel='path-to-the-wheel')
    dependencer.queue(None)
    dependencer._worker()

    # Than I see that the signal was called for the dependency with the right
    # parameters
    callback.assert_called_once_with('dependencer', requirement='sure')
