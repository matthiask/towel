from __future__ import absolute_import, unicode_literals

from django import template
from django.utils.safestring import mark_safe


register = template.Library()


@register.simple_tag
def batch_checkbox(form, id):
    """
    Checkbox which allows selecting objects for batch processing::

        {% for object in object_list %}
            {% batch_checkbox batch_form object.id %}
            {{ object }} etc...
        {% endfor %}

    This tag returns an empty string if ``batch_form`` does not exist for some
    reason. This makes it easier to write templates when you don't know if the
    batch form will be available or not (f.e. because of a permissions
    requirement).
    """

    if not form or not hasattr(form, 'ids'):
        return ''

    cb = '<input type="checkbox" name="batch_%s" value="%s" class="batch" %s>'

    if id in form.ids:
        return cb % (id, id, 'checked="checked" ')

    return mark_safe(cb % (id, id, ''))
