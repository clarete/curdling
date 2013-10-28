.. _error-handling:

==============
Error Handling
==============

Lots of tasks are executed simultaneously the whole time on
curdling. There's currently 4 subservices running multiple threads the
whole time:

* **Finder:** receives requirements and finds URLs;
* **Downloader:** receives URLs and download them whenever ;
* **Curdler:** Builds the package (it forks a process per thread);
* **Dependencer:** Reads the dependencies of a wheel and feeds the
  *Requirement Bucket* in the :ref:`retrieve-and-build`;

Errors might happen in all the above steps, because of broken packages
or resource unavailability. Whenever an error occurs on one of those
services, a `signal will be emitted
<https://github.com/clarete/curdling/blob/master/tests/unit/test_services.py>`_
and the error will be collected.

However, curdling won't stop on the first error. Maybe, in the same
requirement set, there's another requirement of the same package but
with a different version that actually meets the initial
requirements. If curdling manages to recover from that failure, the
error will be logged, but won't be shown to the user unless explicitly
requested.

On the other hand, if curdling can't recover from an error on those
services, it will try to give the most meaningful error report for the
user.

Here's an example of a failure in the **Curdler** when the user tries
to install `gevent <gevent.org>`_ without `libevent
<http://libevent.org/>`_ installed:


.. image:: _static/error1.png


Errors on Curdling
~~~~~~~~~~~~~~~~~~

`Even Knuth wrote broken software
<http://en.wikipedia.org/wiki/Knuth_reward_check>`_ at least once, so
don't expect curdling to be bug free. There are two very important
things on Curdling about errors in its code base:

1) They must be properly logged, so we'll be able to investigate its
   cause;
2) A bug can't be considered closed unless a test that reproduces the
   error can be written;

The installer command is the most complex part of curdling, so users
might face instability under certain environments until Curdling gets
enough field experience.
