"""
Middleware for a lazy ``request.access`` attribute
==================================================
"""


from django.db.models import ObjectDoesNotExist
from django.utils.deprecation import MiddlewareMixin
from django.utils.functional import SimpleLazyObject


def get_access(request):
    try:
        return request.user.access
    except (AttributeError, ObjectDoesNotExist):
        return None


class LazyAccessMiddleware(MiddlewareMixin):
    """
    This middleware (or something equivalent providing a ``request.access``
    attribute must be put in ``MIDDLEWARE_CLASSES`` to use the helpers in
    ``towel.mt``.
    """

    def process_request(self, request):
        request.access = SimpleLazyObject(lambda: get_access(request))
