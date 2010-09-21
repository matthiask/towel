from django import template
from django.db import models
from django.utils.safestring import mark_safe


register = template.Library()


@register.filter
def model_row(instance, fields):
    for name in fields.split(','):
        f = instance._meta.get_field(name)

        if isinstance(f, models.ForeignKey):
            fk = getattr(instance, f.name)
            if hasattr(fk, 'get_absolute_url'):
                value = u'<a href="%s">%s</a>' % (
                    fk.get_absolute_url(),
                    fk)
            else:
                value = unicode(fk)

        elif f.choices:
            value = getattr(instance, 'get_%s_display' % f.name)()

        else:
            value = unicode(getattr(instance, f.name))

        yield (f.verbose_name, value)
