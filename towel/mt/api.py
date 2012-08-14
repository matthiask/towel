from functools import wraps
import httplib

from django.db.models import ObjectDoesNotExist
from django.http import HttpResponse

from towel import api
from towel.utils import safe_queryset_and


def api_access(minimal):
    def _decorator(func):
        @wraps(func)
        def _fn(request, *args, **kwargs):
            if not request.access:
                return HttpResponse('No access', status=httplib.UNAUTHORIZED)

            if request.access.access < minimal:
                return HttpResponse('Insufficient access',
                    status=httplib.UNAUTHORIZED)

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
