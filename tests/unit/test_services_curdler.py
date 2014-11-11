# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
from mock import call, patch, Mock, ANY
from curdling.services import curdler


@patch('curdling.services.curdler.io')
def test_guess_file_type(io):
    "guess_file_type() Should return the format of the archive if such is supported by curdling"

    # Given an archive
    io.open.return_value.__enter__.return_value.read.return_value = \
        io.open.return_value.read.return_value = b"\x1f\x8b\x08"

    # When I try to guess the file type
    file_type = curdler.guess_file_type('pkg.tgz')

    # Then I see that the right file type was found, despite the
    # disguising extension
    file_type.should.equal('gz')


@patch('curdling.services.curdler.io')
def test_guess_file_type_no_matching_type(io):
    "guess_file_type() Should raise UnpackingError if the format is unknown"

    # Given an archive
    with io.open() as patched_io:
        patched_io.read.return_value = b"unsupported format"

        # When I try to guess the file type; Then I see it raises an exception
        curdler.guess_file_type.when.called_with('pkg.tgz').should.throw(
            curdler.UnpackingError, 'Unknown compress format for file pkg.tgz'
        )


@patch('curdling.services.curdler.guess_file_type')
@patch('curdling.services.curdler.zipfile.ZipFile')
def test_unpack(ZipFile, guess_file_type):
    "unpack() Should unpack zip files and return the names inside of the archive"

    # Given a zip package
    guess_file_type.return_value = 'zip'
    ZipFile.return_value.namelist.return_value = ['file.py', 'setup.py']

    # When I try to unpack a file
    open_archive, namelist = curdler.unpack('package.zip')

    # Then I see it returned an open archive
    open_archive.should.equal(ZipFile.return_value)

    # Then I see the right name list being returned
    namelist.should.equal(['file.py', 'setup.py'])


@patch('curdling.services.curdler.guess_file_type')
@patch('curdling.services.curdler.tarfile.open')
def test_unpack_tarball(tarfile_open, guess_file_type):
    "unpack() Should unpack .gz files and return the names inside of the archive"

    # Given a zip package
    guess_file_type.return_value = 'gz'
    file1, file2 = Mock(), Mock()
    file1.name, file2.name = 'file.py', 'setup.py'
    tarfile_open.return_value.getmembers.return_value = [file1, file2]

    # When I try to unpack a file
    open_archive, namelist = curdler.unpack('package.tar.gz')

    # Then I see it returned an open archive
    open_archive.should.equal(tarfile_open.return_value)

    # Then I see the right name list being returned
    namelist.should.equal(['file.py', 'setup.py'])



@patch('curdling.services.curdler.guess_file_type')
def test_unpack_error(guess_file_type):
    "unpack() Should raise `UnpackingError` on unknown files"

    guess_file_type.return_value = None

    # When I try to guess the file type; Then I see it raises an exception
    curdler.unpack.when.called_with('pkg.abc').should.throw(
        curdler.UnpackingError, 'Unknown compress format for file pkg.abc'
    )


def test_find_setup_script():
    "find_setup_script() Should return the setup.py script in the root of an archive's file list"

    # Given the following contents of an archive
    namelist = [
        'pkg-0.1/Makefile',
        'pkg-0.1/README.md',
        'pkg-0.1/setup.py',     # Here's our guy!
        'pkg-0.1/pkg/__init__.py',
        'pkg-0.1/pkg/setup.py',
        'pkg-0.1/pkg/api.py',
        'pkg-0.1/pkg/héhé'.encode('utf8'),
    ]

    # When I look for the setup.py script
    script = curdler.find_setup_script(namelist)

    # Then I see that the right script was found
    script.should.equal('pkg-0.1/setup.py')


def test_cant_find_setup_script():
    "find_setup_script() Should raise an exception when there's no setup.py script in namelist"

    # Given the following contents of an archive
    namelist = [
        'pkg-0.1/Makefile',
        'pkg-0.1/README.md',
        'pkg-0.1/pkg/__init__.py',
        'pkg-0.1/pkg/api.py',
    ]

    # When I look for the setup.py script; Then I see it raises an exception
    script = curdler.find_setup_script.when.called_with(namelist).should.throw(
        curdler.NoSetupScriptFound,
        'No setup.py script found'
    )


@patch('curdling.services.curdler.unpack')
def test_get_setup_from_package(unpack):
    "get_setup_from_package() Should unpack a tarball or zip file and return its setup.py script"

    # Given the following name list of a package
    fp = Mock()
    unpack.return_value = fp, ['pkg-0.1/setup.py', 'pkg-0.1/pkg.py']

    # When I try to retrieve the setup script
    setup_py = curdler.get_setup_from_package('I am a package', '/tmp')

    # Then I see that the package was extracted and that the setup
    # script was found
    setup_py.should.equal('/tmp/pkg-0.1/setup.py')



@patch('curdling.services.curdler.os.listdir')
@patch('curdling.services.curdler.execute_command')
def test_run_script(execute_command, listdir):
    "run_setup_script() Should be able to run the setup.py script and return the correct wheel"

    # Given a patch for `os.listdir` and `execute_command` (see @patch
    # usage in this functions signature)
    listdir.return_value = ['some-other-file', 'wheel-file.whl']

    # When I run the setup script
    wheel = curdler.run_setup_script("/tmp/pkg/setup.py", 'bdist_wheel', '-h')

    # Then I see that the execute command was called with the right
    # parameters
    execute_command.assert_called_once_with(
        ANY, '-c', ANY, 'bdist_wheel', '-h', cwd='/tmp/pkg')

    # And that the wheel was generated in the right directory
    wheel.should.equal('/tmp/pkg/dist/wheel-file.whl')


@patch('curdling.services.curdler.tempfile.mkdtemp')
@patch('curdling.services.curdler.get_setup_from_package')
@patch('curdling.services.curdler.run_setup_script')
@patch('curdling.services.curdler.shutil.rmtree')
def test_curdler_service(rmtree, run_setup_script, get_setup_from_package, mkdtemp):
    "Curdler.handle() Should unpack and build packages"

    destination = mkdtemp.return_value

    # Given a curdler service instance
    service = curdler.Curdler(index=Mock())

    # When I execute the service
    service.handle('tests', {
        'requirement': 'pkg',
        'tarball': 'pkg.tar.gz',
    })

    # Then I see that the `setup.py` script was retrieved using the
    # helper `get_setup_from_package()`.
    get_setup_from_package.assert_called_once_with('pkg.tar.gz', destination)

    # And then I see that the `setup.py` script was run
    run_setup_script.assert_called_once_with(
        get_setup_from_package.return_value, 'bdist_wheel')

    # And then I see that the wheel file should indexed
    service.index.from_file.assert_called_once_with(
        run_setup_script.return_value)

    # And then the temporary destination is removed afterwards
    rmtree.assert_called_once_with(destination)


@patch('curdling.services.curdler.tempfile.mkdtemp')
@patch('curdling.services.curdler.run_setup_script')
@patch('curdling.services.curdler.shutil.rmtree')
def test_curdler_service_build_directory(rmtree, run_setup_script, mkdtemp):

    destination = mkdtemp.return_value

    # Given a curdler service instance
    service = curdler.Curdler(index=Mock())

    # When I execute the service
    service.handle('tests', {
        'requirement': 'pkg',
        'directory': '/tmp/pkg',
    })

    # And then I see that the `setup.py` script was run
    run_setup_script.assert_called_once_with(
        '/tmp/pkg/setup.py', 'bdist_wheel')

    # And then I see that the wheel file should indexed
    service.index.from_file.assert_called_once_with(
        run_setup_script.return_value)

    # And then I see that the temporary destination and the package
    # directory are removed afterwards
    list(rmtree.call_args_list).should.equal([
        call(destination),
        call('/tmp/pkg'),
    ])


@patch('curdling.services.curdler.tempfile.mkdtemp')
@patch('curdling.services.curdler.run_setup_script')
@patch('curdling.services.curdler.shutil.rmtree')
def test_curdler_service_error(rmtree, run_setup_script, mkdtemp):

    destination = mkdtemp.return_value

    # Given a curdler service instance
    service = curdler.Curdler(index=Mock())

    # And then I create a problem in the `run_setup_script` to
    # simulate a build error
    run_setup_script.side_effect = Exception('P0wned!!1')

    # When I execute the service; Then I see that the right exception
    # is raised
    service.handle.when.called_with('tests', {
        'requirement': 'pkg',
        'directory': '/tmp/pkg',
    }).should.throw(Exception, 'P0wned!!1')

    # And then I see that the temporary destination and the package
    # directory are removed afterwards
    list(rmtree.call_args_list).should.equal([
        call(destination),
        call('/tmp/pkg'),
    ])
