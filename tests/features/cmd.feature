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
      usage: __main__.py [-h] [-H] FILE [FILE ...]
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
