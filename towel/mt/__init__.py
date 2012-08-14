"""
towel-multitenancy - Buzzwording everything
"""

def client_model():
    from django.conf import settings
    from django.db.models import loading
    return loading.get_model(*settings.TOWEL_MT_CLIENT_MODEL.split('.'))


def access_model():
    from django.conf import settings
    from django.db.models import loading
    return loading.get_model(*settings.TOWEL_MT_ACCESS_MODEL.split('.'))


class AccessDecorator(object):
    def __new__(cls):
        instance = object.__new__(cls)
        from towel import mt
        mt._access_decorator = instance
        return instance

    def __call__(self, minimal):
        """
        Apply this decorator to all views which should only be reachable by
        authenticated users with sufficient permissions::

            from towel.mt import access
            @access(access.MANAGEMENT)
            def view(request):
                # This view is only available for users with staff and
                # manager access.
        """
        from django.contrib.auth.decorators import login_required
        from django.core.exceptions import PermissionDenied
        from django.db.models import ObjectDoesNotExist
        from django.http import HttpResponse
        from django.utils.functional import wraps

        def decorator(view_func):
            @login_required
            def inner(request, *args, **kwargs):
                if not request.access:
                    return self.handle_missing(request, *args, **kwargs)

                check = self.check_access(request, minimal)

                if check is True:
                    return view_func(request, *args, **kwargs)
                elif isinstance(check, HttpResponse):
                    return check
                raise PermissionDenied('Insufficient permissions')

            fn = wraps(view_func)(inner)
            fn.original_fn = view_func
            return fn
        return decorator

    def check_access(self, request, minimal):
        return request.access.access >= minimal

    def handle_missing(self, request, *args, **kwargs):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied('Missing permissions')
