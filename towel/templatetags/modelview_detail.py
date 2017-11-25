from __future__ import absolute_import, unicode_literals

from django import template
from django.db import models
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _


register = template.Library()


@register.filter
def model_details(instance, fields=None):
    """
    Returns a stream of ``verbose_name``, ``value`` pairs for the specified
    model instance::

        <table>
        {% for verbose_name, value in object|model_details %}
            <tr>
                <th>{{ verbose_name }}</th>
                <td>{{ value }}</td>
            </tr>
        {% endfor %}
        </table>
    """

    if not fields:
        _fields = instance._meta.fields
    else:
        _fields = [
            instance._meta.get_field(f)
            for f in fields.split(',')]

    for f in _fields:
        if f.auto_created:
            continue

        if isinstance(f, models.ForeignKey):
            fk = getattr(instance, f.name)
            if hasattr(fk, 'get_absolute_url'):
                try:
                    value = mark_safe('<a href="%s">%s</a>' % (
                        fk.get_absolute_url(),
                        fk))
                except Exception:  # Whatever.
                    value = fk
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
