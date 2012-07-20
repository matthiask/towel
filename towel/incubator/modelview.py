import json

from django.http import HttpResponse
from django.shortcuts import render

from towel.modelview import ModelView
from towel.utils import changed_regions


class ParentModelView(ModelView):
    def response_edit(self, request, new_instance, form, formsets):
        regions = {}
        self.render_detail(request, {
            'object': new_instance,
            'regions': regions,
            })
        return HttpResponse(
            json.dumps(changed_regions(regions, form.fields.keys())),
            content_type='application/json')

    def render_form(self, request, context, change):
        if change:
            context.setdefault('base_template', 'modal.html')
        return super(ParentModelView, self).render_form(request, context,
            change=change)


class InlineModelView(ModelView):
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
        parent = get_object_or_404(
            # TODO make this generic
            self.parent_class.objects.for_member(request.user.member),
            id=parent,
            )

        request._parent = parent

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
