import json

from django.db import models
from django.forms.models import modelform_factory
from django.http import HttpResponse


def editfields(modelview, request, instance, form_class=None):
    """
    Processes requests for editing regions defined by the ``{% editable %}``
    template tag

    This method assumes that editing permissions have been checked already.

    If the list of fields (passed as ``_edit`` values in either GET or POST)
    contains fields not available on the model itself, this method calls
    ``get_formset_instances()`` with all other fields in the ``formsets``
    keyword argument and assumes that ``get_formset_instances`` will return
    the appropriate formsets.
    """
    # Get base modelform
    if not form_class:
        form_class = modelview.get_form(request, instance=instance,
            change=True)

    # Compile list of fields to be edited. If the base modelform already
    # specifies Meta.fields, make sure that _edit only contains fields
    # which are in Meta.fields as well. We don't have to do anything with
    # Meta.exclude luckily because Meta.exclude always trumps Meta.fields.
    editfields = request.REQUEST.getlist('_edit')

    modelfields, otherfields = [], []
    for f in editfields:
        try:
            modelview.model._meta.get_field(f)
            modelfields.append(f)
        except models.FieldDoesNotExist:
            otherfields.append(f)

    fields = getattr(form_class.Meta, 'fields', None)
    if fields:
        # Do not use sets to preserve ordering
        modelfields = [f for f in modelfields if f in fields]

    if not (modelfields or otherfields):
        return HttpResponse('')

    # Construct new form_class with only a restricted set of fields
    form_class = modelform_factory(modelview.model, form=form_class,
        fields=modelfields)
    formsets = {}

    if request.method == 'POST':
        form = form_class(request.POST, request.FILES, instance=instance)
        if otherfields:
            formsets = modelview.get_formset_instances(request,
                instance=instance, change=True,
                formsets=otherfields)

        if form.is_valid() and all(f.is_valid() for f in formsets.values()):
            instance = form.save()
            for formset in formsets.values():
                formset.save()

            towel_editable = {}
            modelview.render_detail(request, {
                modelview.template_object_name: instance,
                'towel_editable': towel_editable,
                })

            dependencies = towel_editable.get('dependencies', {})
            widgets_to_update = []
            for field in editfields:
                widgets_to_update.extend(dependencies.get(field, []))

            towel_editable = dict((key, value) for key, value
                in towel_editable.items()
                if key in widgets_to_update)

            return HttpResponse(json.dumps(towel_editable))
    else:
        form = form_class(instance=instance)
        if otherfields:
            formsets = modelview.get_formset_instances(request,
                instance=instance, change=True,
                formsets=otherfields)

    return modelview.render(request,
        modelview.get_template(request, 'editfields'),
        modelview.get_context(request, {
            modelview.template_object_name: instance,
            'form': form,
            'formsets': formsets,
            'editfields': editfields,
            }))
