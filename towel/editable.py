import json

from django.core.exceptions import PermissionDenied
from django.db import models
from django.forms.models import modelform_factory
from django.http import HttpResponse

from . import modelview


class ModelView(modelview.ModelView):
    def editfields(self, request, *args, **kwargs):
        instance = self.get_object_or_404(request, *args, **kwargs)

        if not self.editing_allowed(request, instance):
            raise PermissionDenied

        # Get base modelform
        ModelForm = self.get_form(request, instance=instance, change=True)

        # Compile list of fields to be edited. If the base modelform already
        # specifies Meta.fields, make sure that _edit only contains fields
        # which are in Meta.fields as well. We don't have to do anything with
        # Meta.exclude luckily because Meta.exclude always trumps Meta.fields.
        editfields = request.REQUEST.getlist('_edit')

        modelfields, otherfields = [], []
        for f in editfields:
            try:
                self.model._meta.get_field(f)
                modelfields.append(f)
            except models.FieldDoesNotExist:
                otherfields.append(f)

        fields = getattr(ModelForm.Meta, 'fields', None)
        if fields:
            # Do not use sets to preserve ordering
            modelfields = [f for f in modelfields if f in fields]

        if not (modelfields or otherfields):
            return HttpResponse('')

        # Construct new ModelForm with only a restricted set of fields
        ModelForm = modelform_factory(self.model, form=ModelForm, fields=modelfields)
        formsets = {}

        if request.method == 'POST':
            form = ModelForm(request.POST, request.FILES, instance=instance)
            formsets = self.get_formset_instances(request, instance=instance, change=True,
                formsets=otherfields)

            if form.is_valid() and all(f.is_valid() for f in formsets.values()):
                instance = form.save()
                for formset in formsets.values():
                    formset.save()

                towel_editable = {}
                self.render_detail(request, {
                    self.template_object_name: instance,
                    'towel_editable': towel_editable,
                    })

                dependencies = towel_editable.get('dependencies', {})
                widgets_to_update = []
                for field in editfields:
                    widgets_to_update.extend(dependencies.get(field, []))

                towel_editable = dict((key, value) for key, value in towel_editable.items()
                    if key in widgets_to_update)

                return HttpResponse(json.dumps(towel_editable))
        else:
            form = ModelForm(instance=instance)
            formsets = self.get_formset_instances(request, instance=instance, change=True,
                formsets=otherfields)

        return self.render(request,
            self.get_template(request, 'editfields'),
            self.get_context(request, {
                self.template_object_name: instance,
                'form': form,
                'formsets': formsets,
                'editfields': editfields,
                }))
