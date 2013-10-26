# Curdling - A Concurrent package manager for Python

[![Build Status](https://secure.travis-ci.org/clarete/curdling.png)](http://travis-ci.org/clarete/curdling)

# Installing

```python
easy_install curdling
```

or

```python
pip curdling
```

# In a nutshell

What if you could speed up your python builds seamlessly ?
Replace your `pip install` with `curd install` today and feel the difference:

Installing flask with curdling
```bash
~ॐ time curd install flask
Installing: [##########] 100% (6/6)

real	0m2.412s
user	0m1.478s
sys	0m0.669s
```

Installing with pip
```bash
~ॐ time pip install -q flask

real	0m16.359s
user	0m3.036s
sys	0m1.005s
```

## Why is it faster to install with curdling ?

Python has a new<sup>1</sup>
[PEP](http://en.wikipedia.org/wiki/Python_Enhancement_Proposal#Development)
that proposes a binary format for distribution of compiled python
packages called ["wheel"](http://www.python.org/dev/peps/pep-0427/).

Curdling is a concurrent python package installer that smartly
parallelize package discovery, dependency resolution, download,
compiling, caching and installing.

It's like `easy_install` or `pip`, but a lot faster.

<sup>1</sup>: The PEP is "relatively new" from September 2012

# License

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


[![Bitdeli Badge](https://d2weczhvl823v0.cloudfront.net/clarete/curdling/trend.png)](https://bitdeli.com/free "Bitdeli Badge")
[![instanc.es Badge](https://instanc.es/bin/clarete/curdling.png)](http://instanc.es)
