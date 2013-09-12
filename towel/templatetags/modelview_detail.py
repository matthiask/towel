from django import template
from django.db import models
from django.utils.encoding import force_text
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
        _fields = [instance._meta.get_field_by_name(f)[0] for f
            in fields.split(',')]

    for f in _fields:
        if f.auto_created:
            continue

        if isinstance(f, models.ForeignKey):
            fk = getattr(instance, f.name)
            if hasattr(fk, 'get_absolute_url'):
                try:
                    value = mark_safe(u'<a href="%s">%s</a>' % (
                        fk.get_absolute_url(),
                        fk))
                except:  # Whatever.
                    value = force_text(fk)
            else:
                value = force_text(fk)

        elif f.choices:
            value = getattr(instance, 'get_%s_display' % f.name)()

        elif isinstance(f, (models.BooleanField, models.NullBooleanField)):
            value = getattr(instance, f.name)
            value = force_text({
                True: _('yes'),
                False: _('no'),
                None: _('unknown'),
                }.get(value, value))

        else:
            value = force_text(getattr(instance, f.name))

        yield (f.verbose_name, value)
