from datetime import datetime

from django.contrib.auth.models import User
from django.utils.cache import patch_vary_headers
from django.utils import translation
try:
    from threading import local
except ImportError:
    from django.utils._threading_local import local

_thread_locals = local()

def get_current_request():
    return getattr(_thread_locals, 'request', None)

def get_current_user():
    return getattr(get_current_request(), 'user', None)

class ThreadLocals(object):
    """Middleware that stores the request object in thread local storage."""
    def process_request(self, request):
        _thread_locals.request = request


class UserMiddleware(object):
    def process_request(self, request):
        if hasattr(request, 'user') and isinstance(request.user, User):
#            profile = request.user.get_profile()
#            if not profile.language:
#                profile.language = translation.get_language_from_request(request)
#                profile.save()
#            translation.activate(profile.language)

            request.user.last_login = datetime.now()
            request.user.save()
        else:
            language = translation.get_language_from_request(request)
            translation.activate(language)

        request.LANGUAGE_CODE = translation.get_language()

    def process_response(self, request, response):
        patch_vary_headers(response, ('Accept-Language',))
        if 'Content-Language' not in response:
            response['Content-Language'] = translation.get_language()
        translation.deactivate()
        return response
