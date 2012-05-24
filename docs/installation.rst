.. _installation:

=========================
Installation instructions
=========================

This document describes the steps needed to get Towel up and running.

Towel is based on Django_, so you need a working Django_ installation
first. Towel is developed using Django_ 1.3 and will not work with any
earlier version.

Despite being used in production for over a year, there is no stable
release of Towel yet. You should therefore download the code using
Git_::

    $ git clone git://github.com/matthiask/towel.git

Or add the following line to your ``requirements.txt`` file::

    -e git://github.com/matthiask/towel.git#egg=towel

Towel has no dependencies apart from Django_.

You should add ``towel`` to ``INSTALLED_APPS`` if you want to use
the bundled templates and template tags. This isn't strictly
required though.

.. _Django: http://www.djangoproject.com/
.. _Git: http://git-scm.com/
