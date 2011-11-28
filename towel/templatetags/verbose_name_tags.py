import itertools

from django import template


register = template.Library()


PATHS = [
    '_meta', # model
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
    return _resolve(item, 'verbose_name')

@register.filter
def verbose_name_plural(item):
    return _resolve(item, 'verbose_name_plural')
