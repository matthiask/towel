try:
    from functools import wraps
except ImportError:
    from django.utils.functional import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect

from mooch.accounts.models import Profile


def access_level_required(access_level):
    def decorator(view_func):
        @login_required
        def inner(request, *args, **kwargs):
            try:
                profile = request.user.get_profile()
            except Profile.DoesNotExist:
                raise PermissionDenied

            if profile.access_level>=access_level:
                if 'profile' not in kwargs:
                    kwargs['profile'] = profile

                return view_func(request, *args, **kwargs)
            raise PermissionDenied

        fn = wraps(view_func)(inner)
        fn.original_fn = view_func
        return fn
    return decorator
