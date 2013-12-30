"""
Making ``towel.api`` multitenancy-aware
=======================================

All you need is a view decorator handling the permissions and a resource
subclass which makes sure that data is only ever shown from one tenant.
"""

from __future__ import absolute_import, unicode_literals

from functools import wraps

from django.http import HttpResponse
from django.utils.six.moves import http_client

from towel import api
from towel.utils import safe_queryset_and


def api_access(minimal):
    """
    Decorator which ensures that the current ``request.access`` model
    provides at least ``minimal`` access.
    """
    def _decorator(func):
        @wraps(func)
        def _fn(request, *args, **kwargs):
            if not request.access:
                return HttpResponse(
                    'No access',
                    status=http_client.UNAUTHORIZED)

            if request.access.access < minimal:
                return HttpResponse(
                    'Insufficient access',
                    status=http_client.UNAUTHORIZED)

            return func(request, *args, **kwargs)
        return _fn
    return _decorator


class Resource(api.Resource):
    """
    Resource subclass which automatically applies filtering by
    ``request.access`` to all querysets used.
    """
    def get_query_set(self):
        return safe_queryset_and(
            super(Resource, self).get_query_set(),
            self.model.objects.for_access(self.request.access),
        )
