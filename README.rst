Welcome to Curdling
===================

.. image:: https://travis-ci.org/clarete/curdling.png?branch=master
   :target: https://travis-ci.org/clarete/curdling

Curdling is a command line tool for managing Python packages.

It was designed to find, build and cache all the dependencies your
application needs to start up and run smoothly. A solid concurrency
model allows curdling to execute tasks asynchronously, resulting in a
considerable improve in speed over `pip <http://pip-installer.org>`_
and `easy_install
<http://peak.telecommunity.com/DevCenter/EasyInstall>`_.

You should definitely check the `Official Documentation
<http://clarete.github.io/curdling>`_ to learn more about the project.


Installation
------------
::

  $ easy_install curdling

Usage
-----
::

  $ curd install flask

License
-------

Curdling - Concurrent package manager for Python

Copyright (C) 2013  Lincoln Clarete <lincoln@clarete.li>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
