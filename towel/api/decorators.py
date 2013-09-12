from functools import wraps

from django.contrib.auth import authenticate
from django.http import HttpResponse
from django.utils.six.moves import http_client
from django.views.decorators.vary import vary_on_headers


def http_basic_auth(func):
    @wraps(func)
    @vary_on_headers('Authorization')
    def _decorator(request, *args, **kwargs):
        if 'HTTP_AUTHORIZATION' in request.META:
            meth, _, auth = request.META['HTTP_AUTHORIZATION'].partition(' ')
            if meth.lower() == 'basic':
                try:
                    auth = auth.strip().decode('base64')
                except Exception:  # binascii.Error, really.
                    return HttpResponse('Invalid authorization header',
                        status=http_client.BAD_REQUEST)

                username, sep, password = auth.partition(':')
                user = authenticate(username=username, password=password)
                if user:
                    request.user = user

        return func(request, *args, **kwargs)
    return _decorator
