from django import template
from django.template.loader import render_to_string

register = template.Library()


@register.simple_tag
def bar(percentage):
    return render_to_string('_bar.html', {
        'percentage': percentage,
        })
