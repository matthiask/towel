from __future__ import absolute_import, unicode_literals

from django import template
from django.db import models
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _

from towel.templatetags import towel_resources


register = template.Library()


register.inclusion_tag('towel/_pagination.html', takes_context=True)(
    towel_resources.pagination)
register.inclusion_tag('towel/_ordering_link.html', takes_context=True)(
    towel_resources.ordering_link)
register.filter(towel_resources.querystring)


@register.filter
def model_row(instance, fields):
    """
    Shows a row in a modelview object list:

    ::

        {% for object in object_list %}
            <tr>
                {% for verbose_name, field in object|model_row:"name,url" %}
                    <td>{{ field }}</td>
                {% endfor %}
            </tr>
        {% endfor %}

    """

    for name in fields.split(','):
        try:
            f = instance._meta.get_field(name)
        except models.FieldDoesNotExist:
            attr = getattr(instance, name)
            if hasattr(attr, '__call__'):
                yield (name, attr())
            else:
                yield (name, attr)
            continue

        if isinstance(f, models.ForeignKey):
            fk = getattr(instance, f.name)
            if hasattr(fk, 'get_absolute_url'):
                value = mark_safe('<a href="%s">%s</a>' % (
                    fk.get_absolute_url(),
                    fk))
            else:
                value = fk

        elif f.choices:
            value = getattr(instance, 'get_%s_display' % f.name)()

        elif isinstance(f, (models.BooleanField, models.NullBooleanField)):
            value = getattr(instance, f.name)
            value = {
                True: _('yes'),
                False: _('no'),
                None: _('unknown'),
            }.get(value, value)

        else:
            value = getattr(instance, f.name)

        yield (f.verbose_name, value)
