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
version which does nothing if protection is active. If you override the deletion
method for some reason too, you have to ensure that the threadlocal state is
respected too.
"""

from contextlib import contextmanager
from threading import local

from django.db import models


DEFAULT = None
PROTECT = 'protect'

_deletion = local()


def set_mode(mode):
    _deletion.mode = mode


@contextmanager
def protect():
    set_mode(PROTECT)
    yield
    set_mode(DEFAULT)


class Model(models.Model):
    class Meta:
        abstract = True

    def delete(self, *args, **kwargs):
        if getattr(_deletion, 'mode', None) == PROTECT:
            return
        super(Model, self).delete(*args, **kwargs)
