from __future__ import absolute_import, unicode_literals

import re

from django import template
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

from towel.utils import parse_args_and_kwargs, resolve_args_and_kwargs


register = template.Library()


def flatatt(attrs):
    """
    Convert a dictionary of attributes to a single string.
    The returned string will contain a leading space followed by key="value",
    XML-style pairs.  It is assumed that the keys do not need to be
    XML-escaped.  If the passed dictionary is empty, then return an empty
    string.
    """
    return ''.join([
        ' %s="%s"' % (k, conditional_escape(v))
        for k, v in attrs.items()])


@register.tag
def region(parser, token):
    """
    Defines a live-updateable region::

        {% region "identifier" fields="family_name,given_name" tag="div" %}
            {# Template code #}
        {% endregion %}

    The identifier should be a short string which is unique for the whole
    project, or at least for a given view. It is used to identify the region
    when live-updating, it should therefore be usable as a part of a HTML
    ``id`` attribute. The identifer should not start with an underscore,
    those names are reserved for internal bookkeeping.

    ``fields`` is a comma-separated list of fields (or other identifiers)
    which are used inside the given region. It is recommended to use the
    field and relation names here, but you are free to use anything you
    want. It can also be left empty if you purely want to update regions by
    their identifier.

    The ``tag`` argument defines the HTML tag used to render the region.
    The default tag is a ``div``.

    Additional keyword arguments will be rendered as attributes. This can
    be used to specify classes, data attributes or whatever you desire.
    """

    nodelist = parser.parse(('endregion',))
    parser.delete_first_token()

    return RegionNode(
        nodelist, *parse_args_and_kwargs(parser, token.split_contents()[1:]))


class RegionNode(template.Node):
    def __init__(self, nodelist, args, kwargs):
        self.nodelist = nodelist
        self.args = args
        self.kwargs = kwargs

    def render(self, context):
        args, kwargs = resolve_args_and_kwargs(context, self.args, self.kwargs)
        return self._render(context, *args, **kwargs)

    def _render(self, context, identifier, fields='', tag='div', **kwargs):
        regions = context.get('regions')

        region_id = 'twrg-%s' % identifier
        output = self.nodelist.render(context)

        if regions is not None:
            regions[region_id] = output
            dependencies = regions.setdefault('_dependencies', {})

            for field in re.split('[,\s]+', str(fields)):
                dependencies.setdefault(field, []).append(region_id)

        kwargs['id'] = region_id

        return mark_safe('<{tag} {attrs}>{output}</{tag}>'.format(
            attrs=flatatt(kwargs),
            output=output,
            tag=tag,
        ))
