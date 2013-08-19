from mock import patch
from curdling import Curd, hash_files


@patch('io.open')
def test_hashing_files(io_open):
    "It should be possible to get a uniq hash that identifies a list of files"

    # Given that I have a list of files and a mocked content for each one
    file_list = 'a.txt', 'b.txt', 'c.txt'
    io_open.return_value.read.side_effect = ['file1', 'file2', 'file3']

    # When I hash them
    hashed = hash_files(file_list)

    # Then I see that the hash is right
    hashed.should.equal('c9dfd0ebf5a976d3948a923dfa3dd913ddb84f9d')
