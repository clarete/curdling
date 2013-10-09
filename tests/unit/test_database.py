from __future__ import absolute_import, print_function, unicode_literals
from mock import patch, Mock
from curdling.database import Database


@patch('curdling.database.DistributionPath')
def test_check_installed(DistributionPath):
    "It should be possible to check if a certain package is currently installed"

    DistributionPath.return_value.get_distribution.return_value = Mock()
    Database.check_installed('gherkin==0.1.0').should.be.true

    DistributionPath.return_value.get_distribution.return_value = None
    Database.check_installed('gherkin==0.1.0').should.be.false
