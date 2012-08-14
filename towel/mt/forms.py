"""
Forms
=====

These three form subclasses will automatically add limitation by tenant
to all form fields with a ``queryset`` attribute.

.. warning::

    If you customized the dropdown using ``choices`` you have to limit the
    choices by the current tenant yourself.
"""

from django import forms

from towel import forms as towel_forms
from towel.utils import safe_queryset_and


def _process_fields(form, request):
    for field in form.fields.values():
        if getattr(field, 'queryset', None):
            model = field.queryset.model

            field.queryset = safe_queryset_and(
                field.queryset,
                model.objects.for_access(request.access),
                )


class Form(forms.Form):
    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request')
        super(Form, self).__init__(*args, **kwargs)
        _process_fields(self, request)


class ModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request')
        super(ModelForm, self).__init__(*args, **kwargs)
        _process_fields(self, request)


class SearchForm(towel_forms.SearchForm):
    def post_init(self, request):
        _process_fields(self, request)
