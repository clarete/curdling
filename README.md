Curdling
========

Curdles your cheesy code and extracts its binaries

## tl;dr

Curdling compiles all the packages you request into
[wheel](www.python.org/dev/peps/pep-0427/), cache them locally and use the
clients to build packages the server doesn't have. Now keep reading, it's worth
it!

## Intro

Installing python packages using [pip](http://www.pip-installer.org/) is an
easy thing, you just `pip install` your package and BOOM, it usually works. It
might take a while though. Packages such as
[lxml](https://pypi.python.org/pypi/lxml) and a few other extensions that must
be compiled might take minutes to build (~6min on travis ci).

Life is too short to wait for dependency installation. Let's spend our CPU
cycles in something cooler.

## So, what's the idea behind curdling?

Basically [Wheels](www.python.org/dev/peps/pep-0427/)! I'm not reinventing them
though. The new python binary format brought hope to my heart. Curdling is
basically a cache layer on top of the python package installation environment
(which is kinda crazy). Curdling leverages the power of *wheel* and
[distlib](https://bitbucket.org/vinay.sajip/distlib) to provide a seamless
package installation and update.

### Seriously? what curdling does?

So, curdling is just a pile of small services, called when something specific
needs to be done. To illustrate how it works, let's say we want to install
[forbidden fruit](http://clarete.github.io/forbiddenfruit). To do so, you can
just issue the following command:

    $ curdling forbiddenfruit

BOOM! The requested package is now installed in your `sys.path`! But wait, what
happened under the hood? Let's study each step:

1. The package needs to be found and downloaded;
2. If it's not a wheel package, build it;
3. Install the wheel;

### Taking a deeper look

Where does the package come from? By default, from [pypi](http://pypi.python.org).
But you can inform your own `pypi` repositories using the option `-i` as many
times as you want, just like this:

    $ curdling forbiddenfruit -i http://localhost:8080/simple -i http://friendscomp/simple

Just remember, if you use `-i` you'll replace the default repository. If you
want to use the default and an extra one you have to type both manually.

Well, how that can be better compared to *pip*? So, *pypi* compatible indexes
are not the only repositories you can use with *curdling*. There's also the
**curdling index**. If you use the `-c` option instead of `-i`, it will try to
download *wheels* from another *curdling* directory shared through *HTTP*. When
it happens, you just skip the build process which is just the slowest in this
whole story in most of the cases.

So, what happens if your curdling cache doesn't contain the requested package?
Well, the client will download it from another source (you can either use `-i`
or trust the default *pypi* repository)

After downloading, building and installing your package, if ran with `-u`
*curdling* will also try to send the compiled package back to the servers you
informed with `-c`.
