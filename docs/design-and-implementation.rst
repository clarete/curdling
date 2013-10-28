.. _design-and-implementation:

=========================
Design and Implementation
=========================

Curdling is a concurrent package manager for Python. Its most
noticeable feature is the package installer. Just like `pip install`,
the command `curd install` will find requirements in external
repositories, build and install packages for you. But blazingly fast.

The install command is focused on both speed and accuracy. Curdling
will always try to find the best version for a requirement set.

The **Retrieve and Build** stage will do the find, build and
dependency check. This initial cycle won’t finish until we ensure that
all the requested requirements were processed.

In the sequence, the **Wheel Installer** will ensure that all the
requirements initially requested by the user were found during the
*R&B* process; then it will install everything for you. These and all
the other subsystems of the installer are going to be studied in depth
in the next sections.


.. _retrieve-and-build:

Retrieve and build process
--------------------------

Partial representation of the *R&B* flow:

.. image:: _static/pnet.svg
   :alt: Petri Net representation of the "Retrieve and Build" process
   :width: 600px

This process basically reads requirements from both the `-r
requirements.txt` file and from the command line arguments (curd
install <packages>). Let's imagine the following call::

    $ curd install Flask

**What we want**

* Flask is the package you want to install in your environment.
* We're also interested in the package dependencies

**Problems we have**

* We have to build the package before retrieving the dependency list.

**What should happen**

1) Find out which packages we want to install (read more about command
   line parsing in the file curdling/tool/__init__.py)
2) Feed the "Requirement Producer" with the package found in the
   command line
3) The requirement will be sent to the "Finder" component;
4) The finder component uses a modified version of the
   `distlib.locators.SimpleScraperLocator` to find packages on PyPi
   compatible repos;
5) If the package was found, its link will be sent to the downloader;
6) The downloader *do not* download duplicated items. They'll be
   discarded.
7) If the downloader finds the package, it will send to the curdler
   component
8) The curdler (builder) will uncompress the package and run its
   `setup.py`.
9) After building the package, we'll actually generate the wheel
   calling `setup.py` again using the `bdist_wheel` subcommand.
10) So we finally, have a wheel file. The path for this file will be
    sent to the "Dependency Checker";
11) The dependency checker will yield each dependency found and it
    will start the same process for the next package;
12) After finding all the dependencies, the checker will forward the
    wheel to the installer queue;
13) The installer queue contains packages, not requirements. So, every
    time we need to add a new package to that queue, we have to find a
    compatible version among all the ones downloaded for that specific
    package;

Steps from 2 to 13 will be repeated for each dependency found.

Install Wheels
--------------

This is the second step after populating the installer queue. When
this queue is full and the previous step is finished. We'll just
consume the whole list and install the wheels required by the user and
all its dependencies collected during the R&B process.