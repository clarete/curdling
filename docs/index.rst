:orphan:

Welcome to Curdling
===================

Curdling is a command line tool for managing Python packages. It was
designed to find, build and cache all the dependencies your app needs
to start up and run smoothly. A solid concurrency model allows
curdling to find, download and build software faster than any other
package installer we currently have.

The content of this website is divided into two main parts. The
:ref:`usage` teaches you how to use with curdling to manage your
packages. The :ref:`design-and-implementation` section shows in depth
how curdling works.

Quick Start
-----------

If you just want to install curdling and trying out. Try the following
commands

**To install curdling**
::

  $ easy_install curdling

**To use curdling**
::

  $ curd install flask

Contents
========

.. toctree::
   :maxdepth: 3

   usage
   distributed-cache
   design-and-implementation
