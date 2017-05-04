"""
Assumptions
===========

* The following settings are required:

  * ``TOWEL_MT_CLIENT_MODEL``:
    The tenant model, e.g. ``clients.Client``.
  * ``TOWEL_MT_ACCESS_MODEL``:
    The model linking a Django user with a client, must have the following
    fields:

      * ``user``: Foreign key to ``auth.User``.
      * ``access``: An integer describing the access level of the given user.
        Higher numbers mean higher access. You have to define those numbers
        yourself.
      * The lowercased class name of the client model above as a foreign key
        to the client model. If your client model is named ``Customer``, the
        name of this foreign key must be ``customer``.

* All model managers have a ``for_access()`` method with a single argument,
  an instance of the access model, which returns a queryset containing only
  the objects the current user is allowed to see. The access model should be
  available as ``request.access``, which means that you are free to put
  anything there which can be understood by the ``for_access()`` methods. The
  ``request.access`` attribute is made available by the
  ``towel.mt.middleware.LazyAccessMiddleware`` middleware.
* ``towel.mt.modelview.ModelView`` automatically fills in a ``created_by``
  foreign key pointing to ``auth.User`` if it exists.
* The form classes in ``towel.mt.forms``, those being ``ModelForm``, ``Form``
  and ``SearchForm`` all require the request (the two former on initialization,
  the latter on ``post_init``). Model choice fields are postprocessed to only
  contain values from the current tenant. This does not work if you customize
  the ``choices`` field at the same time as setting the ``queryset``. If you
  do that you're on your own.
* The model authentication backend ``towel.mt.auth.ModelBackend`` also allows
  email addresses as username. It preloads the access and client model and
  assigns it to ``request.user`` if possible. This is purely a convenience --
  you are not required to use the backend.
"""

from __future__ import absolute_import, unicode_literals


def client_model():
    from django.apps import apps
    from django.conf import settings
    return apps.get_model(*settings.TOWEL_MT_CLIENT_MODEL.split('.'))


def access_model():
    from django.apps import apps
    from django.conf import settings
    return apps.get_model(*settings.TOWEL_MT_ACCESS_MODEL.split('.'))


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
