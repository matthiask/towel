import re

from django import template
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

from towel.utils import parse_args_and_kwargs, resolve_args_and_kwargs


register = template.Library()


def generate_counter(start=0):
    while True:
        yield start
        start += 1


def flatatt(attrs):
    """
    Convert a dictionary of attributes to a single string.
    The returned string will contain a leading space followed by key="value",
    XML-style pairs.  It is assumed that the keys do not need to be XML-escaped.
    If the passed dictionary is empty, then return an empty string.
    """
    return u''.join([u' %s="%s"' % (k, conditional_escape(v)) for k, v in attrs.items()])


@register.tag
def editable(parser, token):
    nodelist = parser.parse(('endeditable',))
    parser.delete_first_token()

    return EditableNode(nodelist,
        *parse_args_and_kwargs(parser, token.split_contents()[1:]))


class EditableNode(template.Node):
    def __init__(self, nodelist, args, kwargs):
        self.nodelist = nodelist
        self.args = args
        self.kwargs = kwargs

    def render(self, context):
        args, kwargs = resolve_args_and_kwargs(context, self.args, self.kwargs)
        return self._render(context, *args, **kwargs)

    def _render(self, context, edit=None, used=None):
        output = self.nodelist.render(context)
        if edit is None and used is None:
            return output
        elif used is None:
            used = edit

        try:
            counter = context['towel_editable_counter']
        except KeyError:
            counter = context.dicts[0]['towel_editable_counter'] = generate_counter()

        ident = 'towel_editable_%s' % counter.next()

        try:
            towel_editable = context['towel_editable']
            towel_editable[ident] = output

            dependencies = towel_editable.setdefault('dependencies', {})

            for field in used.split(','):
                dependencies.setdefault(field, []).append(ident)

        except KeyError:
            # Ignore this silently -- towel_editable will not be available most of the time
            pass

        attrs = {
            'id': ident,
            }
        if edit:
            attrs['class'] = 'towel_editable'
            attrs['data-edit'] = edit
        if used:
            attrs['data-used'] = used

        return mark_safe('<span %s>%s</span>' % (flatatt(attrs), output))
