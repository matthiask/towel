"""
``ModelView``
=============
==
As long as you use this class, everything should just work (tm).
"""

from __future__ import absolute_import, unicode_literals

from towel import modelview as towel_modelview

import towel.mt
from towel.mt.forms import ModelForm


class ModelView(towel_modelview.ModelView):
    """
    This model view subclass ensures that all querysets are already
    restricted to the current client.

    Furthermore, it requires certain access levels when accessing its
    views; the required access defaults to ``access.MANAGER`` (the
    highest access level), but can be overridden by setting
    ``view_access`` or ``crud_access`` when instantiating the model
    view.
    """

    #: Default access level for all views
    view_access = None

    #: Default access level for CRUD views, falls back to ``view_access``
    #: if not explicitly set
    crud_access = None

    #: The editing form class, defaults to ``towel.mt.forms.ModelForm``
    #: instead of ``django.forms.ModelForm``
    form_class = ModelForm

    def view_decorator(self, func):
        return towel.mt._access_decorator(self.view_access)(func)

    def crud_view_decorator(self, func):
        return towel.mt._access_decorator(
            self.crud_access or self.view_access)(func)

    def get_query_set(self, request, *args, **kwargs):
        return self.model.objects.for_access(request.access)

    def get_form_instance(self, request, form_class, instance=None,
                          change=None, **kwargs):
        args = self.extend_args_if_post(request, [])
        kwargs.update({
            'instance': instance,
            'request': request,  # towel.mt.forms needs that
        })

        return form_class(*args, **kwargs)
