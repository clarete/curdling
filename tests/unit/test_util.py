from __future__ import absolute_import, print_function, unicode_literals
from mock import call, patch, Mock, ANY
from curdling import util
import io


@patch('io.open')
def test_expand_requirements(open_func):
    "It should be possible to include other files inside"

    # Given that I have two files, called `development.txt` and
    # `requirements.txt` with the following content:
    open_func.return_value.read.side_effect = (
        '-r requirements.txt\nsure==0.2.1\n',  # development.txt
        'gherkin==0.1.0\n\n\n',                # requirements.txt
    )

    # When I expand the requirements
    requirements = util.expand_requirements('development.txt')

    # Then I see that all the required files were retrieved
    requirements.should.equal([
        'gherkin (== 0.1.0)',
        'sure (== 0.2.1)',
    ])


@patch('io.open')
def test_expand_commented_requirements(open_func):
    "expand_requirements() should skip commented lines"

    # Given that I have a file `development.txt` and with the following
    # content:
    open_func.return_value.read.return_value = (
        '# -r requirements.txt\n\n\n'   # comment
        'gherkin==0.1.0\n\n\n'          # requirements.txt
    )

    # When I expand the requirements
    requirements = util.expand_requirements('development.txt')

    # Then I see that all the required files were retrieved
    requirements.should.equal([
        'gherkin (== 0.1.0)',
    ])


@patch('io.open')
def test_expand_requirements_ignore_http_links(open_func):
    "It should be possible to parse files with http links"

    # Given that I have a file `development.txt` and with the following
    # content:
    open_func.return_value.read.return_value = (
        'sure==0.2.1\nhttp://python.org'
    )

    # When I expand the requirements
    requirements = util.expand_requirements('development.txt')

    # Then I see that all the required files were retrieved
    requirements.should.equal([
        'sure (== 0.2.1)',
        'http://python.org',
    ])


def test_filehash():
    "filehash() should return the hash file objects"

    # Given that I have a file instance
    fp = io.BytesIO(b'My Content')

    # When I call the filehash function
    hashed = util.filehash(fp, 'md5')

    # Then I see the hash was right
    hashed.should.equal('a86c5dea3ad44078a1f79f9cf2c6786d')


def test_spaces():
    "spaces() should add spaces to paragraphs"

    # Given that I have a paragraph of text
    text = '''phrase 1
phrase 2
phrase 3'''

    # When I add spaces to the above text
    spaced = util.spaces(4, text)

    # Then I see each line starting with the right amount of spaces
    spaced.should.equal('''    phrase 1
    phrase 2
    phrase 3''')


def test_get_auth_info_from_url():
    "get_auth_info_from_url() should be able to extract authentication data from a URL"

    # Given that I have a URL that contains authentication info
    url = "http://user:password@domain.org"

    # When I try to get the authentication information
    authentication_information = util.get_auth_info_from_url(url)

    # Then I see both user and password are correct
    authentication_information.should.equal({
        'authorization': 'Basic dXNlcjpwYXNzd29yZA=='})


@patch('curdling.util.subprocess')
def test_execute_command_when_it_fails(subprocess):
    "execute_command() will raise an exception if the command fails"

    # Given that my process will definitely fail
    subprocess.Popen.return_value.returncode = 1
    subprocess.Popen.return_value.communicate.return_value = ["stdout", "stderr"]

    # When I execute the command; Then I see it raises the right exception
    # containing the stderr of the command we tried to run
    util.execute_command.when.called_with('ls').should.throw(Exception, "stderr")
