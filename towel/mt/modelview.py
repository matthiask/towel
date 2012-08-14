"""
``ModelView``
=============

As long as you use this class, everything should just work (tm).
"""

from django.contrib.auth.models import User
from django.db import models
from django.forms.models import modelform_factory
from django.http import HttpResponse

from towel import modelview as towel_modelview
from towel.forms import towel_formfield_callback

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

    def view_decorator(self, func):
        return towel.mt._access_decorator(self.view_access)(func)

    def crud_view_decorator(self, func):
        return towel.mt._access_decorator(
            self.crud_access or self.view_access)(func)

    def get_query_set(self, request, *args, **kwargs):
        return self.model.objects.for_access(request.access)

    def get_formfield_callback(self, request):
        return towel_formfield_callback

    def get_form(self, request, instance=None, change=None, **kwargs):
        kwargs.setdefault('formfield_callback',
            self.get_formfield_callback(request))
        kwargs.setdefault('form', self.form_class or ModelForm)

        return modelform_factory(self.model, **kwargs)

    def get_form_instance(self, request, form_class, instance=None,
            change=None, **kwargs):
        args = self.extend_args_if_post(request, [])
        kwargs.update({
            'instance': instance,
            'request': request,  # towel.mt.forms needs that
            })

        return form_class(*args, **kwargs)

    def save_model(self, request, instance, form, change):
        Client = towel.mt.client_model()
        client_attr = Client.__name__.lower()
        try:
            if self.model._meta.get_field(client_attr).rel.to == Client:
                setattr(instance, client_attr, getattr(
                    request.access, client_attr))
        except models.FieldDoesNotExist:
            pass

        try:
            if (self.model._meta.get_field('created_by').rel.to == User
                    and not instance.created_by_id):
                instance.created_by = request.user
        except models.FieldDoesNotExist:
            pass

        instance.save()
