.. _installation:

=========================
Installation instructions
=========================

This document describes the steps needed to get Towel up and running.

Towel is based on Django_, so you need a working Django_ installation
first. Towel is mainly developed using the newest release of Django_, but
should work with Django_ 1.4 up to the upcoming 1.7 and with Python_ 2.7
and 3.3. Towel does not currently support Python_ 3.2 but patches adding
support are welcome.

Towel can be installed using the following command::

    $ pip install Towel

Towel has no dependencies apart from Django_.

You should add ``towel`` to ``INSTALLED_APPS`` if you want to use
the bundled templates and template tags. This isn't strictly
required though.

.. _Django: http://www.djangoproject.com/
.. _Python: http://www.python.org/
