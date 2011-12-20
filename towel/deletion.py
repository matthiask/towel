"""
Helper module to circumvent Django's (arguably) broken formset saving behavior
where models are directly deleted even if ``commit=False`` is passed to the
formset's ``save()`` method.

Usage::

    class SafeModel(deletion.Model):
        # fields etc.


Saving formsets::

    with deletion.protect():
        objects = formset.save()

    for obj in formset.deleted_objects: # Django provides this attribute
        obj.delete() # Or do something else, like checking whether the instance
                     # should really be deleted

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
