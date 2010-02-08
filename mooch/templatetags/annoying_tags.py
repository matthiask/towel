from django import template

register = template.Library()


@register.filter
def has(obj, var):
    return var in obj


@register.filter(name='getattr')
def _getattr(obj, name):
    try:
        return obj[name]
    except (TypeError, KeyError):
        try:
            return getattr(obj, name)
        except (TypeError, AttributeError):
            return None
