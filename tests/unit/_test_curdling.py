import os
from datetime import datetime
from mock import patch, call
from curdling.old import CurdManager, Curd, hash_files


@patch('curdling.old.io.open')
def test_hashing_files(io_open):
    "It should be possible to get a uniq hash that identifies a list of files"

    # Given that I have a list of files and a mocked content for each one
    file_list = 'a.txt', 'b.txt', 'c.txt'
    io_open.return_value.read.side_effect = ['file1', 'file2', 'file3']

    # When I hash them
    hashed = hash_files(file_list)

    # Then I see that the hash is right
    hashed.should.equal('c9dfd0ebf5a976d3948a923dfa3dd913ddb84f9d')


@patch('curdling.old.os.stat')
def test_curd(stat):
    "It should be possible to represent a directory with wheels"

    stat.return_value.st_ctime = 1376943600  # mocking data that will feed
                                             # datetime

    # Given that I have a new instance of a curd
    curd = Curd('/path/to/my/curd/container', 'curd_id')

    # Then I can see that all the attributes were correctly set
    curd.uid.should.equal('curd_id')
    curd.path.should.equal('/path/to/my/curd/container/curd_id')
    curd.created.should.equal(datetime(2013, 8, 19, 16, 20))


def test_curd_comparison():
    "It should be possible to compare a curd to another one"

    # Given that I have two curd instances in the same folder with the same ID
    curd1 = Curd('/path/to/my/curd/container', 'curd_id')
    curd2 = Curd('/path/to/my/curd/container', 'curd_id')

    # When I compare them
    same = curd1 == curd2

    # Then I see they're equal
    same.should.be.true


@patch('curdling.old.os.listdir')
def test_curd_members(listdir):
    "It should be possible to list the wheels inside of a curd"

    # Given that I have a curd
    curd = Curd('/path/to/my/curd/container', 'curd_id')

    # When I list the curd members
    curd.members()

    # Then I see the `listdir` function was called against the right path
    listdir.assert_called_once_with('/path/to/my/curd/container/curd_id')



# ---- curd manager ----


@patch('curdling.old.hash_files', lambda l: ','.join(l))
def test_curd_manager_add_files():
    "It should be possible to add new combinations of files to be hashed"

    # Given that I have a manager
    manager = CurdManager('/path/to/the/curd/container')

    # When I add new files
    uid = manager.add(['f1.txt', 'f2.txt'])

    # Then I see the internal mapping was updated and the return value is just
    # the result of the hash func
    uid.should.equal('f1.txt,f2.txt')
    manager.mapping.should.equal({
        'f1.txt,f2.txt': ['f1.txt', 'f2.txt'],
    })


@patch('curdling.old.pip')
def test_curd_manager_new(pip):
    "It should be possible to create new curds through the `CurdManager`"

    # Since we're testing creating a new curd, we don't really need to be
    # careful with the IO performed by the following methods. Let's just kill
    # them for now:
    class MyManager(CurdManager):
        def get(self, uid):
            return None

        def curd_path(self, uid):
            return os.path.join(self.path, uid)

    # Given that I have a manager (with pre-added curd ids)
    manager = MyManager('/path/to/the/curd/container', {
        'index-url': 'http://pip1.org',
        'extra-index-url': 'http://pip2.org',
    })
    manager.mapping['my-curd'] = ('file1.txt', 'file2.txt')

    # When I call the function that actually creates the new curd
    curd = manager.new('my-curd')

    # Then I see that `pip` was properly called under the hood
    list(pip.wheel.call_args_list).should.equal([
        call(
            r='file1.txt',
            wheel_dir='/path/to/the/curd/container/my-curd',
            extra_index_url='http://pip2.org',
            index_url='http://pip1.org',
            quiet=True,
        ),
        call(
            r='file2.txt',
            wheel_dir='/path/to/the/curd/container/my-curd',
            extra_index_url='http://pip2.org',
            index_url='http://pip1.org',
            quiet=True,
        )
    ])


@patch('curdling.old.pip')
def test_curd_manager_install(pip):
    "It should be possible to install packages from wheels stored in curds"

    # Since we're testing installing a newly created curd, we don't really need
    # to be careful with the IO performed by the following methods. Let's just
    # kill them for now:
    class MyManager(CurdManager):
        def get(self, uid):
            return None

        def curd_path(self, uid):
            return os.path.join(self.path, uid)

    # Given that I have a manager (with pre-added curd ids)
    manager = MyManager('/path/to/the/curd/container')
    manager.mapping['my-curd'] = ('file1.txt', 'file2.txt')

    # When I call the function that actually creates the new curd
    curd = manager.install('my-curd')

    # Then I see that `pip` was properly called under the hood
    list(pip.install.call_args_list).should.equal([
        call(
            r='file1.txt',
            use_wheel=True,
            no_index=True,
            find_links='/path/to/the/curd/container/my-curd',
            quiet=True,
        ),
        call(
            r='file2.txt',
            use_wheel=True,
            no_index=True,
            find_links='/path/to/the/curd/container/my-curd',
            quiet=True,
        )
    ])
