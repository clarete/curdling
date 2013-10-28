.. _next-steps:

==========
Next steps
==========

Although curdling was born to be fast and stable, there will still be
issues and new features to add, that will recursively bring us more
bugs.

With that in mind, curdling was written on top of a very robust test
structure so we are definitely prepared to move forward fast with less
problems.

Ideas for the near future
~~~~~~~~~~~~~~~~~~~~~~~~~

There's still a list of very important features that were not
implemented so far. Here's a list of some remarkable ones:

* The cache system doesn't take the `PEP 0425
  <http://www.python.org/dev/peps/pep-0425/>`_ into account. Meaning
  that remote cache servers can't be shared among users running
  different OS's for example.

* Curdling can't be ran more than once simultaneously on the same
  computer. The cache present on ``$HOME/.curds`` is not prepared to
  be accessed by more than one process at the same time. It would lead
  to corrupted files and other IO failures.
