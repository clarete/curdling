import os

from shutil import rmtree
from datetime import datetime
from curdling import CurdManager, Curd, hash_files
from curdling.server import Server

from sure import scenario
from mock import patch, Mock
from . import FIXTURE


def setup_server(context):
    # Setting up a manager that uses our dummy pypi server running on the port
    # 8000. This will create a curd to be served in the next step by our
    # server.
    manager = CurdManager(
        FIXTURE('project2', '.curds'),
        {'index-url': 'http://localhost:8000/simple'})
    context.uid = manager.add([FIXTURE('project2', 'requirements.txt')])
    manager.new(context.uid)

    # Retrieving the response of the server without spinning the whole http
    # stuff up. I crave a usable asynchronous API for python!
    server = Server(manager, __name__)
    client = server.test_client()

    # Creating a patched urlopen to replace the original one by this fake one
    # that contains the output read using the test client
    url = '/{}'.format(context.uid)
    response = Mock()
    response.getcode.return_value = 200
    response.bosta = 200
    response.read.side_effect = lambda: client.get(url).data

    context.patch = patch('curdling.urllib2.urlopen', lambda p: response)


def cleandir(context):
    if os.path.isdir(FIXTURE('project1', '.curds')):
        for curd in os.listdir(FIXTURE('project1', '.curds')):
            rmtree(FIXTURE('project1', '.curds', curd))


@scenario(cleandir)
def test_hashing_files(context):
    "It should be possible to get a uniq hash that identifies a list of files"

    # Given that I have a list of files and a mocked content for each one
    file_list = (
        FIXTURE('project1', 'requirements.txt'),
        FIXTURE('project1', 'development.txt'),
    )

    # When I hash them
    hashed = hash_files(file_list)

    # Then I see that the hash is right
    hashed.should.equal('682f87d84c80d0a85c9179de681b3474906113b3')


@scenario(cleandir)
def test_no_curd(context):
    "CurdManager.get() should return None when it can't find a specific curd"

    # Given that I have an instance of a curd manager
    curd_manager = CurdManager(FIXTURE('project1', '.curds'))

    # When I try to get a curd I know that does not exist
    curd = curd_manager.get('I-know-you-dont-exist')

    # Then I see it returns None
    curd.should.be.none


@scenario(cleandir)
def test_new_curd(context):
    "It should be possible to create new curds based on requirements files"

    # Given that I have a file that contains a list of dependencies of a fake
    # project
    manager = CurdManager(
        FIXTURE('project1', '.curds'),
        {'index-url': 'http://localhost:8000/simple'})
    requirements = (
        FIXTURE('project1', 'requirements.txt'),
        FIXTURE('project1', 'development.txt'),
    )
    uid = manager.add(requirements)

    # When I create the new curd
    curd = manager.new(uid)

    # Then I see the curd was downloaded correctly created
    os.path.isdir(FIXTURE('project1', '.curds')).should.be.true
    os.path.isdir(FIXTURE('project1', '.curds', uid)).should.be.true

    (os.path.isfile(FIXTURE('project1', '.curds', uid, 'gherkin-0.1.0-py27-none-any.whl'))
        .should.be.true)
    (os.path.isfile(FIXTURE('project1', '.curds', uid, 'forbiddenfruit-0.1.0-py27-none-any.whl'))
        .should.be.true)


@scenario(cleandir)
def test_has_curd(context):
    "It should be possible to find curds saved locally"

    # Given that I have a curd hash, a curd manager linked to a curdcache
    curd_id = '682f87d84c80d0a85c9179de681b3474906113b3'
    path = FIXTURE('project1', '.curds')
    settings = {'index-url': 'http://localhost:8000/simple'}
    manager = CurdManager(path, settings)
    curd = manager.new(manager.add([
        FIXTURE('project1', 'requirements.txt'),
        FIXTURE('project1', 'development.txt'),
    ]))

    # When I retrieve the unknown curd
    curd = manager.get(curd.uid)

    # Then I see that my curd was properly retrieved
    curd.should.be.a(Curd)
    curd.uid.should.equal(curd_id)
    curd.path.should.equal(os.path.join(path, curd_id))

    # mocking the created prop
    with patch('os.stat') as stat:
        stat.return_value.st_ctime = 1376943600
        curd.created.should.equal(datetime(2013, 8, 19, 16, 20))


@scenario(cleandir)
def test_find_cached_curds(context):
    "It should be possible to find cached curds"

    # Given that I have a newly created curd
    manager = CurdManager(
        FIXTURE('project1', '.curds'),
        {'index-url': 'http://localhost:8000/simple'})
    uid = manager.add([FIXTURE('project1', 'requirements.txt')])

    curd1 = manager.new(uid)

    # When I try to get the same curd instead of creating it
    with patch('curdling.pip') as pip:
        curd2 = manager.new(uid)

        # Then I see that the pip command was not called in the second time
        pip.wheel.called.should.be.false

    # Then I see curd1 and curd2 are just the same object
    curd1.should_not.be.none
    curd1.should.equal(curd2)


@scenario(cleandir)
def test_list_curds(context):
    "It should be possible to list available curds in a manager"

    # Given that I have a newly created curd
    manager = CurdManager(
        FIXTURE('project1', '.curds'),
        {'index-url': 'http://localhost:8000/simple'})
    curd1 = manager.new(manager.add([
        FIXTURE('project1', 'requirements.txt')]))

    # When I list all the curds
    curds = manager.available()

    # Then I see that the curd1 that I just created is inside of the list
    curds.should.contain(curd1)


@scenario([cleandir, setup_server])
def test_retrieve_remote_curd(context):
    "It should be possible to retrieve remote curds and install them locally"

    # Given that I have curdle manager (with a curd) configured with a remote
    # cache url
    manager = CurdManager(
        FIXTURE('project1', '.curds'),
        {'cache-url': 'http://localhost:8001'})  # where does this addr come
                                                 # from? See `setup_server()`

    # When I retrieve a curd
    with context.patch:                       # Both context.{patch,uid} come from
        curd = manager.retrieve(context.uid)  # from `setup_server()`

    # Then I see the curd was correctly retrieved
    os.path.isdir(curd.path).should.be.true
    (os.path.isfile(os.path.join(curd.path, 'gherkin-0.1.0-py27-none-any.whl'))
     .should.be.true)
