.. _installation:

=========================
Installation instructions
=========================

This document describes the steps needed to get Towel up and running.

Towel is based on Django_, so you need a working Django_ installation
first. Towel requires Python_ 3 and Django_ 3.2 or newer.

The latest stable release can be installed from PyPI_ using the
following command::

    $ pip install towel

Towel has no dependencies apart from Django_.

You should add ``towel`` to ``INSTALLED_APPS`` if you want to use
the bundled templates and template tags. This isn't strictly
required though.

.. _Django: https://www.djangoproject.com/
.. _Python: https://www.python.org/
.. _PyPI: https://pypi.org/project/towel/
