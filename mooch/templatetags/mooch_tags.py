from django import template
from django.template.loader import render_to_string
from django.utils.text import capfirst

from mooch import generic

register = template.Library()


@register.simple_tag
def bar(percentage):
    return render_to_string('_bar.html', {
        'percentage': percentage,
        })


@register.simple_tag
def ordering_link(request, field, title):
    title = capfirst(title)

    if not hasattr(request, '_ordering_link_cache'):
        data = request.GET and request.GET.copy() or {}

        # Remove pagination and ordering vars
        for k in ('o', 'ot', 'page'):
            if k in data:
                del data[k]

        request._ordering_link_cache = (
            request.GET.get('o', ''),
            request.GET.get('ot') == 'desc' and 'desc' or 'asc',
            generic.querystring(data),
            )

    c = request._ordering_link_cache
    tmpl = u'<a href="?%s%s" class="%s">%s</a>'

    if c[0] == field:
        dir = c[1] == 'asc' and 'desc' or 'asc'
        return tmpl % (
            c[2],
            u'&o=%s&ot=%s' % (
                field,
                dir,
                ),
            c[1],
            title,
            )

    return tmpl % (
        c[2],
        u'&o=%s' % field,
        'asc',
        title,
        )
