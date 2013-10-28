.. _distributed-cache:

=================
Distributed Cache
=================

Curdling was initially designed to speed up builds on `Continuous
Integration <http://en.wikipedia.org/wiki/Continuous_integration>`_
servers. So, remote caching for packages found and compiled by
curdling was always a top priority.

Built-in Server
===============

Curdling provides a built-in cache server for `binary packages
<http://www.python.org/dev/peps/pep-0427/>`_, so every machine that
runs curdling is a potential cache server.

Extra dependencies
~~~~~~~~~~~~~~~~~~

The dependencies for the built-in server must be installed
separately. The following command will do the job::

  $ curd install curdling[server]

Running the cache server
~~~~~~~~~~~~~~~~~~~~~~~~
::

  $ curd-server /path/to/a/folder/full/of/wheels

That's right, your cache server is running and all the computers that
have access to this machine through HTTP can use your cache.

Available command line arguments::

  $ curd-server [-h] [-d] [-H HOST] [-p PORT] [-u USER_DB] DIRECTORY

* ``-h``, ``--help``: Shows a friendly help text;
* ``-d``, ``--debug``: Runs a pure `Flask <http://flask.pocoo.org>`_
  app with the `debug` flag set to True. Do not use in production;
* ``-H``, ``--host=HOST``: Which interface to bind the server;
  Defaults to ``0.0.0.0``;
* ``-p``, ``--port=PORT``: Port number; Defaults to ``8000``;
* ``-u``, ``--user-db=USER_DB``: Path to an `htpasswd
  <http://httpd.apache.org/docs/2.2/programs/htpasswd.html>`_
  compatible file. Notice that the only currently supported algorithm
  is ``crypto``.


Cache Client
============


Retrieving wheels from the cache server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In order to retrieve wheels from the remote caching server, the client
needs to inform the server address through the ``-c`` parameter. E.g::

  $ curd install -c http://user:passwd@localhost:8000

Notice that the password will be exposed through commands like ``ps``,
be careful.

Automatic upload of built packages
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As mentioned before, Curdling was initially designed to speed up tests
on CI servers. So, the built-in cache server was written. However,
it's still pretty annoying to setup a huge infrastructure to feed the
cache server.

Curdling solves that problem by using clients to warm up the cache
server on their first run. Meaning that, if a cache server is informed
through the ``-c`` parameter, all the missing requirements will be
retrieved from another source (probably `PyPi
<http://pypi.python.org>`_), they'll be compiled, installed and then
the client will upload the packages back to the curdling server if the
parameter ``-u`` is used::

  $ curd install -c http://localhost:8000 -u flask

With the above command, curdling will try to retrieve ``flask`` from
the local cache. If it's not available, it will fall back to the
regular Python repositories.

After retrieving, building and installing the required package, the
``curd`` command will upload the wheels back to the cache server.

Notice that the authentication also works for pushing packages, so
it's safe to run your own server with packages you don't want to share
with anyone else.
