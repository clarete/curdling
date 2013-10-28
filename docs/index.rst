:orphan:

Welcome to Curdling
===================

Curdling is a command line tool for managing Python packages.

It was designed to find, build and cache all the dependencies your
application needs to start up and run smoothly. A solid concurrency
model allows curdling to execute tasks asynchronously, resulting in a
considerable improve in speed over `pip <http://pip-installer.org>`_
and `easy_install
<http://peak.telecommunity.com/DevCenter/EasyInstall>`_.

The content of this website is divided into two main parts. The
:ref:`usage` teaches you how to use with curdling to manage your
packages. The :ref:`design-and-implementation` section shows in depth
how curdling works.

See it rolling
~~~~~~~~~~~~~~

Click the terminal to play (also available at `asciinema
<http://asciinema.org/a/6122>`_)

.. raw:: html

   <div class="c-player-container">
     <script src="http://asciinema.org/a/6122.js" id="asciicast-6122" async></script>
     <script>
     window.setTimeout(function(){
       $('.asciicast iframe').ready(function() {
         $('.asciicast iframe').width('100%').height('35px');});}, 300)</script>
  </div>


Noticeable Features
~~~~~~~~~~~~~~~~~~~

* Robust Concurrent model: it's **FAST**!
* Really good :ref:`error-handling` and Report;
* Conflict resolution for repeated requirements;
* Distributed Cache System that includes a built-in cache server;
* Simple command line interface;
* Usage of bleeding edge technology available in the Python community;
* Concurrent and Parallel, but :kbd:`Ctrl`-:kbd:`C` still works;

Why curdling and not pip?
~~~~~~~~~~~~~~~~~~~~~~~~~

Pip is awesome! I've been using it for managing my Python packages for
a while now. However, its code base is just too complex, which makes
it hard to iterate fast on its development and implement exciting new
features in a reasonable time.

Cache for binary packages
-------------------------

Among other features listed in this documentation, I also wrote
curdling because I work on a project that depends on 167 external
libraries, including ``lxml``, ``numpy`` and ``pygmagic``. Curdling is
faster than pip because it caches the binary packages compiled when
the ``setup.py`` script is ran. Curdling also provides a
:ref:`distributed-cache`, so you can share your compiled packages with
other environments. Build once, use everywhere we can!


Motivation
~~~~~~~~~~

Almost every Python developer knows how to install a third party
library in a `virtualenv <http://www.virtualenv.org/en/latest/>`_ with
`pip <http://pip-installer.org>`_. It works fairly well, but it could
be faster.

Curdling was born to decrease the time taken by dependency
installation in the Continuous Integration Server that tests software
at `Yipit <http://yipit.com>`_. We managed to decrease the build time
*~70%* by replacing **pip** with Curdling.


Installation
~~~~~~~~~~~~
::

  $ easy_install curdling


Contents
========

.. toctree::
   :maxdepth: 3

   usage
   error-handling
   distributed-cache
   design-and-implementation
   next-steps
