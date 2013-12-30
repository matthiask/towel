from __future__ import absolute_import, unicode_literals

from functools import reduce
import operator

from django import template
from django.utils import six
from django.utils.http import urlencode


register = template.Library()


@register.inclusion_tag('towel/_pagination.html', takes_context=True)
def pagination(context, page, paginator, where=None):
    """
    Shows pagination links::

        {% pagination current_page paginator %}

    The argument ``where`` can be used inside the pagination template to
    discern between pagination at the top and at the bottom of an object
    list (if you wish). The default object list template passes
    ``"top"`` or ``"bottom"`` to the pagination template. The default
    pagination template does nothing with this value though.
    """

    return {
        'context': context,
        'page': page,
        'paginator': paginator,
        'where': where,
    }


@register.filter
def querystring(data, exclude='page,all'):
    """
    Returns the current querystring, excluding specified GET parameters::

        {% request.GET|querystring:"page,all" %}
    """

    exclude = exclude.split(',')

    items = reduce(
        operator.add,
        (list((k, v) for v in values) for k, values
            in six.iterlists(data) if k not in exclude),
        [])

    return urlencode(sorted(items))


@register.inclusion_tag('towel/_ordering_link.html', takes_context=True)
def ordering_link(context, field, request, title='', base_url='', **kwargs):
    """
    Shows a table column header suitable for use as a link to change the
    ordering of objects in a list::

        {% ordering_link "" request title=_("Edition") %} {# default order #}
        {% ordering_link "customer" request title=_("Customer") %}
        {% ordering_link "state" request title=_("State") %}

    Required arguments are the field and the request. It is very much
    recommended to add a title too of course.

    ``ordering_link`` has an optional argument, ``base_url`` which is
    useful if you need to customize the link part before the question
    mark. The default behavior is to only add the query string, and nothing
    else to the ``href`` attribute.

    It is possible to specify a set of CSS classes too. The CSS classes
    ``'asc'`` and ``'desc'`` are added automatically by the code depending
    upon the ordering which would be selected if the ordering link were
    clicked (NOT the current ordering)::

        {% ordering_link "state" request title=_("State") classes="btn" %}

    The ``classes`` argument defaults to ``'ordering'``.
    """

    current = request.GET.get('o', '')

    # Automatically handle search form persistency
    data = request.GET.copy()
    if not data:
        form = context.get('search_form')
        if form is not None and getattr(form, 'persistency', False):
            data = form.data

    ctx = {
        'querystring': querystring(data, exclude='page,all,o'),
        'field': field,
        'used': current in (field, '-%s' % field),
        'descending': current == field,
        'title': title,
        'base_url': base_url,
    }
    ctx.update(kwargs)
    return ctx
