import json

from django.core.exceptions import PermissionDenied
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
        # specifies Meta.fields, make sure that _editfields only contains fields
        # which are in Meta.fields as well. We don't have to do anything with
        # Meta.exclude luckily because Meta.exclude always trumps Meta.fields.
        editfields = request.REQUEST.getlist('_editfields')
        fields = getattr(ModelForm.Meta, 'fields', None)
        if fields:
            # Do not use sets to preserve ordering
            editfields = [f for f in editfields if f in fields]

        # Construct new ModelForm with only a restricted set of fields
        ModelForm = modelform_factory(self.model, form=ModelForm, fields=editfields)

        if request.method == 'POST':
            form = ModelForm(request.POST, request.FILES, instance=instance)

            if form.is_valid():
                instance = form.save()

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

        return self.render(request,
            self.get_template(request, 'editfields'),
            self.get_context(request, {
                self.template_object_name: instance,
                'form': form,
                'editfields': editfields,
                }))
