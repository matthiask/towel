import operator
import urllib

from django import template
from django.db import models
from django.utils.safestring import mark_safe


register = template.Library()


@register.filter
def model_row(instance, fields):
    for name in fields.split(','):
        try:
            f = instance._meta.get_field(name)
        except models.FieldDoesNotExist:
            attr = getattr(instance, name)
            if hasattr(attr, '__call__'):
                yield (name, attr())
            yield (name, attr)
            continue

        if isinstance(f, models.ForeignKey):
            fk = getattr(instance, f.name)
            if hasattr(fk, 'get_absolute_url'):
                value = mark_safe(u'<a href="%s">%s</a>' % (
                    fk.get_absolute_url(),
                    fk))
            else:
                value = unicode(fk)

        elif f.choices:
            value = getattr(instance, 'get_%s_display' % f.name)()

        else:
            value = unicode(getattr(instance, f.name))

        yield (f.verbose_name, value)


@register.inclusion_tag('_pagination.html', takes_context=True)
def pagination(context, page, paginator, where=None):
    return {
        'context': context,
        'page': page,
        'paginator': paginator,
        'where': where,
        }


@register.filter
def querystring(data, exclude='page,all'):
    exclude = exclude.split(',')

    items = reduce(operator.add,
        (list((k, v.encode('utf-8')) for v in values) for k, values in data.iterlists() if k not in exclude),
        [])

    return urllib.urlencode(items)
