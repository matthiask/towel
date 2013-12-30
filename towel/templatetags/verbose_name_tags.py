from __future__ import absolute_import, unicode_literals

import itertools

from django import template


register = template.Library()


PATHS = [
    '_meta',
    'queryset.model._meta',
    'instance._meta',
    'model._meta',
]


def _resolve(instance, last_part):
    for path in PATHS:
        o = instance
        found = True
        for part in itertools.chain(path.split('.'), [last_part]):
            try:
                o = getattr(o, part)
            except AttributeError:
                found = False
                break

        if found:
            return o


@register.filter
def verbose_name(item):
    """
    Pass in anything and it tries hard to return its ``verbose_name``::

        {{ form|verbose_name }}
        {{ object|verbose_name }}
        {{ formset|verbose_name }}
        {{ object_list|verbose_name }}
    """
    return _resolve(item, 'verbose_name')


@register.filter
def verbose_name_plural(item):
    """
    Pass in anything and it tries hard to return its ``verbose_name_plural``::

        {{ form|verbose_name_plural }}
        {{ object|verbose_name_plural }}
        {{ formset|verbose_name_plural }}
        {{ object_list|verbose_name_plural }}
    """
    return _resolve(item, 'verbose_name_plural')
