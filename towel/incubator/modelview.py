import json

from django.forms.models import model_to_dict
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, render

from towel.modelview import ModelView
from towel.utils import changed_regions


class EditLiveModelView(ModelView):
    #: The form class used for live editing. Should only contain fields
    #: for which editing through the editlive mechanism is allowed.
    editlive_form = None

    def editlive(self, request, *args, **kwargs):
        if not self.editlive_form:
            raise Http404('No live editing support.')

        instance = self.get_object_or_404(request, *args, **kwargs)

        data = model_to_dict(instance,
            fields=self.editlive_form._meta.fields,
            exclude=self.editlive_form._meta.exclude,
            )

        for key, value in request.POST.items():
            data[key] = value

        form = self.editlive_form(data, instance=instance, request=request)

        if form.is_valid():
            project = form.save()
            return self.response_edit(request, form.save(), form, {})

        # FIXME the content is alert()ed on the other side. That's ugly.
        return HttpResponse(unicode(form.errors))


class ParentModelView(EditLiveModelView):
    def response_edit(self, request, new_instance, form, formsets):
        regions = {}
        self.render_detail(request, {
            self.template_object_name: new_instance,
            'regions': regions,
            })
        return HttpResponse(
            json.dumps(changed_regions(regions, form.changed_data)),
            content_type='application/json')

    def render_form(self, request, context, change):
        if change:
            context.setdefault('base_template', 'modal.html')
        return super(ParentModelView, self).render_form(request, context,
            change=change)


class InlineModelView(EditLiveModelView):
    parent_attr = 'parent'

    @property
    def parent_class(self):
        return self.model._meta.get_field(self.parent_attr).rel.to

    def get_object(self, request, *args, **kwargs):
        if 'pk' in kwargs:
            kwargs[self.parent_attr] = kwargs.pop('parent')
        return super(InlineModelView, self).get_object(
            request, *args, **kwargs)

    def add_view(self, request, parent):
        request._parent = get_object_or_404(self.parent_class, id=parent)
        return super(InlineModelView, self).add_view(request)

    def save_model(self, request, instance, form, change):
        if hasattr(request, '_parent'):
            setattr(instance, self.parent_attr, request._parent)
        instance.save()

    def response_add(self, request, instance, *args, **kwargs):
        regions = {}
        opts = self.parent_class._meta
        render(request,
            '%s/%s_detail.html' % (opts.app_label, opts.module_name), {
                'object': getattr(instance, self.parent_attr),
                'regions': regions,
                })
        return HttpResponse(
            json.dumps(changed_regions(regions, [
                '%s_set' % self.model.__name__.lower(),
                ])),
            content_type='application/json')

    response_delete = response_edit = response_add
    # TODO what about response_adding_denied, response_editing_denied and
    # response_deletion_denied?
