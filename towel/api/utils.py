from functools import reduce
import operator

from django.utils.encoding import force_text
from django.utils.http import urlencode


def querystring(data, exclude=(), **kwargs):
    """
    Returns a properly encoded querystring

    The supported arguments are as follows:

    - ``data`` should be a ``MultiValueDict`` instance (i.e. ``request.GET``)
    - ``exclude`` is a list of keys from ``data`` which should be skipped
    - Additional key-value pairs are accepted as keyword arguments

    Usage::

        next_page_url = querystring(
            request.GET,
            exclude=('page',),
            page=current + 1,
            )
    """
    items = reduce(operator.add, (
        list((k, v) for v in values)
        for k, values in data.lists() if k not in exclude
        ), [])

    for key, value in kwargs.items():
        items.append((key, force_text(value)))

    return urlencode(sorted(items))
