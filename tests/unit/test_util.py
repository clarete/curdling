from __future__ import absolute_import, print_function, unicode_literals
from mock import call, patch, Mock, ANY
from curdling import util
import io


@patch('io.open')
def test_expand_requirements(open_func):
    "It should be possible to include other files inside"

    # Given that I have a file called "development.txt"
    development_txt = Mock()
    development_txt.read.return_value = \
        '-r requirements.txt\nsure==0.2.1\n'

    # And a file called "requirements_txt"
    open_func.return_value.read.return_value = 'gherkin==0.1.0\n\n\n'

    # When I expand the file "development.txt"
    requirements = util.expand_requirements(development_txt)

    # Then I see that the requirement present in "development.txt" was
    # included, as well as the one present in "requirements.txt",
    # referenced using the '-r' option
    requirements.should.equal([
        'gherkin (0.1.0)',
        'sure (0.2.1)',
    ])


def test_expand_commented_requirements():
    "expand_requirements() should skip commented lines"

    # Given the file "development.txt"
    development_txt = Mock()
    development_txt.read.return_value = (
        '# -r requirements.txt\n\n'
        'gherkin==0.1.0\n\n\n'
    )

    # When I expand the file
    requirements = util.expand_requirements(development_txt)

    # Then I see that all the required files were retrieved and the
    # comments were omitted
    requirements.should.equal([
        'gherkin (0.1.0)',
    ])


def test_expand_requirements_parse_http_links():
    "It should be possible to parse files with http links"

    # Given the file "development.txt"
    development_txt = Mock()
    development_txt.read.return_value = (
        'sure==0.2.1\nhttp://python.org'
    )

    # When I expand the file
    requirements = util.expand_requirements(development_txt)

    # Then I see that all the required files were retrieved
    requirements.should.equal([
        'sure (0.2.1)',
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


def test_get_auth_info_from_url_no_auth_info():
    "get_auth_info_from_url() Should return an empty dictionary if no authentication info is found in the URL"

    # Given that I have a URL that contains authentication info
    url = "http://domain.org"

    # When I try to get the authentication information
    authentication_information = util.get_auth_info_from_url(url)

    # Then I see that the authentication information is just empty
    authentication_information.should.equal({})


@patch('curdling.util.subprocess')
def test_execute_command(subprocess):
    "execute_command() Should return None when the subprocess runs successfully"

    # Given that my process will definitely fail
    subprocess.Popen.return_value.returncode = 0
    subprocess.Popen.return_value.communicate.return_value = ["stdout", "stderr"]

    # When I execute the command; Then I see it raises the right exception
    # containing the stderr of the command we tried to run
    util.execute_command('ls').should.be.none


@patch('curdling.util.subprocess')
def test_execute_command_when_it_fails(subprocess):
    "execute_command() Should raise an exception if the command fails"

    # Given that my process will definitely fail
    subprocess.Popen.return_value.returncode = 1
    subprocess.Popen.return_value.communicate.return_value = ["stdout", "stderr"]

    # When I execute the command; Then I see it raises the right exception
    # containing the stderr of the command we tried to run
    util.execute_command.when.called_with('ls').should.throw(Exception, "stderr")


def test_safe_constraints():
    "safe_constraints() Should return a string with all the constraints of a requirement separated by comma"

    util.safe_constraints('curdling (== 0.3.3, >= 0.3.2)').should.equal(
        '0.3.3, >= 0.3.2')

    util.safe_constraints('curdling').should.be.none

    util.safe_constraints('http://codeload.github.com/clarete/curdling').should.be.none
