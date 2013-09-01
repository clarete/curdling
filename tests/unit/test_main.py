from pkg_resources import Requirement
from mock import patch

from curdling.util import parse_requirements, expand_requirements


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
    requirements = expand_requirements('development.txt')

    # Then I see that all the required files were retrieved
    requirements.should.equal([
        {'name': 'gherkin', 'spec': ('==', '0.1.0'), 'extras': []},
        {'name': 'sure', 'spec': ('==', '0.2.1'), 'extras': []},
    ])


def test_parsing_requirements():
    "It should be possible to parse requirements"

    # Given that I have the following requirements file
    requirements = '''
gherkin==0.1.0
forbiddenfruit==0.1.1
'''

    # When I parse it
    requirements_list = parse_requirements(requirements)

    # Then I see I got the right list
    requirements_list.should.equal([
        {'name': 'gherkin', 'spec': ('==', '0.1.0'), 'extras': []},
        {'name': 'forbiddenfruit', 'spec': ('==', '0.1.1'), 'extras': []},
    ])
