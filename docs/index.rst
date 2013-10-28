:orphan:

Welcome to Curdling
===================

Curdling is a command line tool for managing Python packages.

It was designed to find, build and cache all the dependencies your
application needs to start up and run smoothly. A solid concurrency
model allows curdling to execute tasks asynchronously, resulting in a
considerable improve in speed over `PIP <http://pip-installer.org>`_
and `easy_install
<http://peak.telecommunity.com/DevCenter/EasyInstall>`_.

The content of this website is divided into two main parts. The
:ref:`usage` teaches you how to use with curdling to manage your
packages. The :ref:`design-and-implementation` section shows in depth
how curdling works.

Noticeable Features
-------------------

* Robust Concurrent model: it's **FAST**!
* Conflict resolution for repeated requirements;
* Distributed Cache System that includes a built-in cache server;
* Simple command line interface;
* Usage of bleeding edge technology available in the Python community;


Motivation
----------

Almost every Python developer knows how to install a third party
library in a `virtualenv <http://www.virtualenv.org/en/latest/>`_ with
`PIP <http://pip-installer.org>`_. It works fairly well, but it could
be faster.

Curdling was born to decrease the time taken by dependency
installation in the Continuous Integration Server that tests software
at `Yipit <http://yipit.com>`_. We managed to decrease the build in
*~70%* by replacing **PIP** by Curdling.


Installation
------------
::

  $ easy_install curdling


Contents
========

.. toctree::
   :maxdepth: 3

   usage
   distributed-cache
   design-and-implementation
   next-steps
