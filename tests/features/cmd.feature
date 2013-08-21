Feature: Command Line API
  In order to use curdling locally
  As a software maintainer
  I need to interact with a command

  Scenario: Getting basic help
    Given that I have a project called "ProjectX"
    And a file called "ProjectX/requirements.txt" with:
      """
      sure==1.2.2
      """
    When I run "python -m curdling"
    Then I should see:
      """
      usage: __main__.py [-h] [-H] [-r REMOTE_CACHE_URL] [-p PYPI_URL]
                         [-p2 PYPI_URL_2] [-s SERVER]
                         FILE [FILE ...]
      __main__.py: error: too few arguments
      """

  Scenario: Getting the hash of a list of files
    Given that I have a project called "ProjectY"
    And a file called "ProjectY/requirements.txt" with:
      """
      forbiddenfruit==0.1.0
      """
    And a file called "ProjectY/development.txt" with:
      """
      sure==1.2.2
      """
    When I run "python -m curdling -H requirements.txt development.txt"
    Then I should see:
      """
      65193a9f55493e79b4e2441372eb631bdcfbec53
      """

  Scenario: Installing packages using curdled packages installed through pip
    Given that I have a project called "ProjectZ"
    And a file called "ProjectZ/requirements.txt" with:
      """
      gherkin==0.1.0
      forbiddenfruit==0.1.0
      """
    When I run "python -m curdling -p http://localhost:8000/simple requirements.txt"
    Then I should see:
      """
      [info] No cache found
      [info] No external cache informed, using pip to curdle
      [info] Curdling
      [info] Installing curdled packages
      """
    And I ensure that "gherkin==0.1.0" is installed
    And I ensure that "forbiddenfruit==0.1.0" is installed


  Scenario: Installing packages through a remotely cached curd
    Given that I have a project called "CurdCache"
    And a file called "CurdCache/requirements.txt" with:
      """
      gherkin==0.1.0
      """
    And I run the server with "python -m curdling -p http://localhost:8000/simple -s localhost:8001 requirements.txt"
    And that I have a project called "CacheConsumer"
    And a file called "CacheConsumer/requirements.txt" with:
      """
      gherkin==0.1.0
      """
    When I run "python -m curdling -r http://localhost:8001 requirements.txt"
    Then I should see:
      """
      [info] No cache found
      [info] Looking for curds in the given url
      [info] Installing curdled packages
      """
    And I ensure that "gherkin==0.1.0" is installed
    And I shutdown the server
