from django.db.models import ObjectDoesNotExist
from django.utils.functional import SimpleLazyObject


def get_access(request):
    try:
        return request.user.access
    except (AttributeError, ObjectDoesNotExist):
        return None


class LazyAccessMiddleware(object):
    def process_request(self, request):
        request.access = SimpleLazyObject(lambda: get_access(request))
