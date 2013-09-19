from __future__ import absolute_import, print_function, unicode_literals
import os

# Those are functional tests, I need to do some IO and all the files I have are
# located in the `fixtures` folder. The following line is just a shortcut to
# build absolute paths pointing to things inside of that folder.
FIXTURE = lambda *p: os.path.join(os.path.dirname(__file__), 'fixtures', *p)
