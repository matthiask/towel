"""
Helper module to circumvent Django's (arguably) broken formset saving behavior
where models are directly deleted even if ``commit=False`` is passed to the
formset's ``save()`` method.

Usage::

    class SafeModel(deletion.Model):
        # fields etc.


    instance = SafeModel.objects.get(...)
    with deletion.protect():
        instance.delete() # Does nothing
    instance.delete() # Actually deletes the instance!


Saving formsets::

    with deletion.protect():
        objects = formset.save()

    for obj in formset.deleted_objects: # Django provides this attribute
        obj.delete() # Or do something else, like checking whether the instance
                     # should really be deleted


This is achieved by overriding the model's ``delete()`` method with a different
version which does nothing if protection is active. If you override the
deletion method for some reason too, you have to ensure that the threadlocal
state is respected too.
"""

from __future__ import absolute_import, unicode_literals

from contextlib import contextmanager
from threading import local

from django.db import models


DEFAULT = None
PROTECT = 'protect'

_deletion = local()


def set_mode(mode):
    """
    Sets the protection mode. The argument should be one of:

    - ``deletion.DEFAULT``:
      Standard behavior, instances are deleted.
    - ``deletion.PROTECT``:
      ``delete()`` invocations on models inheriting ``deletion.Model`` are
      ignored.
    """
    _deletion.mode = mode


@contextmanager
def protect():
    """
    Wraps a code block with deletion protection

    Example::

        from towel import deletion

        instance = SafeModel.objects.get(...)
        with deletion.protect():
            # Does nothing
            instance.delete()

        # Actually deletes the instance
        instance.delete()
    """
    set_mode(PROTECT)
    yield
    set_mode(DEFAULT)


class Model(models.Model):
    """
    Safe model base class, inherit this model instead of the standard
    :py:class:`django.db.models.Model` if you want to take advantage of
    the :py:mod:`towel.deletion` module.
    """
    class Meta:
        abstract = True

    def delete(self, *args, **kwargs):
        """
        Deletion is skipped if inside a :py:func:`~towel.deletion.protect`
        block.
        """
        if getattr(_deletion, 'mode', None) == PROTECT:
            return
        super(Model, self).delete(*args, **kwargs)
