from django import template
from django.template.loader import render_to_string
from django.utils.text import capfirst

register = template.Library()


@register.simple_tag
def bar(percentage):
    return render_to_string('_bar.html', {
        'percentage': percentage,
        })


@register.simple_tag
def ordering_link(field, current_ordering, querystring_ordering, title):
    ordering = '&o=%s' % field
    if current_ordering in ((field, 'asc'), (field, None)):
        ordering += '&ot=desc'

    return '<a href="?%s%s">%s</a>' % (
        querystring_ordering,
        ordering,
        capfirst(title))
