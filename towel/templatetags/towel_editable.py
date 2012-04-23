import re

from django import template
from django.utils.safestring import mark_safe

from towel.utils import parse_args_and_kwargs, resolve_args_and_kwargs


register = template.Library()


def generate_counter(start=0):
    while True:
        yield start
        start += 1


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

        return mark_safe(
            u'<span id="%s" class="towel_editable" data-editfields="%s" data-visiblefields="%s">%s</span>' % (
                ident, edit, used, output))
