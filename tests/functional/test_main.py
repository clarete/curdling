import os
from . import FIXTURE
from curdling.download import DirectoryStorage


def test_directory_storage():
    "It should be possible to save files to directories in the local disk"

    # Given the following directory storage
    storage = DirectoryStorage(path=FIXTURE('storagedirtest'))

    # When I save a file to the storage
    storage.write('path/to/a/file.txt', 'the content')

    # Then I see that this file exists after the above call
    result_path = FIXTURE('storagedirtest', 'path', 'to', 'a', 'file.txt')
    os.path.exists(result_path).should.be.true

    # And that the file above has the same content
    open(result_path).read().should.equal('the content')

    # And I clean things up
    del storage


def test_directory_storage_dict_api():
    "The DirectoryStorage component should provide a dict-like API"

    # Given the following directory storage
    storage = DirectoryStorage(path=FIXTURE('storagedirtest1'))

    # When I save a file to the storage
    storage['path/to/a/file.txt'] = 'the content'

    # Then I see that this file exists after the above call
    result_path = FIXTURE('storagedirtest1', 'path', 'to', 'a', 'file.txt')
    os.path.exists(result_path).should.be.true

    # And that the file above has the same content
    open(result_path).read().should.equal('the content')

    # And I delete the whole directory
    del storage


def test_directory_storage_delete_file():
    "It should be possible to delete files from the storage"

    # Given the following directory storage with a file
    storage = DirectoryStorage(path=FIXTURE('storagedirtest2'))
    storage['file/to/be/deleted.txt'] = 'some content'

    # When I blow it up
    os.path.exists(FIXTURE('storagedirtest2/file/to/be/deleted.txt')).should.be.true
    del storage['file/to/be/deleted.txt']

    # Then I see the file doesn't exist anymore
    os.path.exists(FIXTURE('storagedirtest2/file/to/be/deleted.txt')).should.be.false

    # Removing the storage directory
    del storage


def test_directory_storage_delete():
    "It should be possible to remove the whole storage"

    # Given the following directory storage (and save a file to create the
    # dirs)
    storage = DirectoryStorage(path=FIXTURE('storagedirtest3'))
    storage['blah'] = 'yo'

    # When I blow it up
    del storage

    # Then I see the file doesn't exist anymore
    os.path.isdir(FIXTURE('storagedirtest3')).should.be.false
