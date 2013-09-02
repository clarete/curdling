import os
import shutil
import tarfile

from StringIO import StringIO
from json import loads
from flask import url_for

from curdling.old import CurdManager
from curdling.server import Server

from sure import scenario
from . import FIXTURE


def cleandir(context):
    path = FIXTURE('project1', '.curds')
    os.path.exists(path) and shutil.rmtree(path)


@scenario(cleandir)
def test_hit_the_first_page(context):
    "It should be possible hit the first page empty"

    # Given that I have the test client
    manager = CurdManager(FIXTURE('project1', '.curds'))
    client = Server(manager, __name__).test_client()

    # When I hit the main page of the api
    result = client.get('/')

    # Then I see it returned nothing, since we have no curds yet
    result.status_code.should.equal(200)
    loads(result.data).should.equal([])


@scenario(cleandir)
def test_list_available_curds(context):
    "It should be possible to list available curds"

    manager = CurdManager(
        FIXTURE('project1', '.curds'),
        {'index-url': 'http://localhost:8000/simple'})
    uid = manager.add([FIXTURE('project1', 'requirements.txt')])

    # Given that I have a manager with a curd and an http client
    client = Server(manager, __name__).test_client()
    curd = manager.new(uid)

    # When I try to list all the available curds
    result = client.get('/')

    # Then I see that the newly created curd is available in the response list
    loads(result.data).should.equal([{
        'uid': uid,
        'url': '/{}'.format(uid),
    }])


@scenario(cleandir)
def test_retrieve_curd(context):
    "It should be possible to download tar packages with curds"

    manager = CurdManager(
        FIXTURE('project1', '.curds'),
        {'index-url': 'http://localhost:8000/simple'})
    uid = manager.add([FIXTURE('project1', 'requirements.txt')])

    # Given that I have an http client that exposes the server API that
    # currently contains a curd
    curd = manager.new(uid)
    app = Server(manager, __name__)
    client = app.test_client()

    # When I try to retrieve the curd page
    with app.test_request_context():
        result = client.get(url_for('curd', uid=curd.uid))

    # Then I see I received a tar package containing the wheel of the package
    # described inside of the `requirements` file
    result.status_code.should.equal(200)
    result.mimetype.should.equal('application/tar')

    # And I see that the tar file received contains the right package list
    tar = tarfile.open(
        name='{}.tar'.format(uid),
        mode='r',
        fileobj=StringIO(result.data))
    [info.name for info in tar].should.equal([
        'gherkin-0.1.0-py27-none-any.whl',
    ])
