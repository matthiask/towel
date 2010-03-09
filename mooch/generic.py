from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.forms.formsets import all_valid
from django.forms.models import modelform_factory
from django.http import Http404
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.encoding import force_unicode
from django.utils.translation import ugettext as _


class ModelView(object):
    view_decorator = lambda self, f: f
    template_object_list_name = 'object_list'
    template_object_name = 'object'

    def __init__(self, model, **kwargs):
        self.model = model
        for k, v in kwargs.items():
            setattr(self, k, v)

    def get_queryset(self, request):
        return self.model.objects.all()

    def get_template(self, request, action):
        opts = self.model._meta
        return '%s/%s_%s.html' % (opts.app_label, opts.module_name, action)

    def get_urls(self):
        from django.conf.urls.defaults import patterns, url
        info = self.model._meta.app_label, self.model._meta.module_name

        return patterns('',
            url(r'^$', self.view_decorator(self.list_view),
                name='%s_%s_list' % info),
            url(r'^add/$', self.view_decorator(self.add_view),
                name='%s_%s_add' % info),
            url(r'^(.+)/$', self.view_decorator(self.detail_view),
                name='%s_%s_detail' % info),
            url(r'^(.+)/edit/$', self.view_decorator(self.edit_view),
                name='%s_%s_edit' % info),
            url(r'^(.+)/delete/$', self.view_decorator(self.delete_view),
                name='%s_%s_delete' % info),
            )

    @property
    def urls(self):
        return self.get_urls()

    # HELPERS

    def get_object(self, request, object_pk):
        queryset = self.get_queryset(request)
        model = queryset.model

        try:
            object_pk = model._meta.pk.to_python(object_pk)
            return queryset.get(pk=object_pk)
        except (model.DoesNotExist, ValidationError):
            raise self.model.DoesNotExist

    def get_form(self, request, **kwargs):
        return modelform_factory(self.model, **kwargs)

    def message(self, request, message):
        messages.info(request, message)

    def save(self, request, obj, form, change):
        obj.save()

    def save_formset(self, request, form, formset, change):
        formset.save()

    # VIEW HELPERS

    def render_list(self, request, context):
        return render_to_response(
            self.get_template(request, 'list'),
            context)

    def render_detail(self, request, context):
        return render_to_response(
            self.get_template(request, 'detail'),
            context)

    def render_form(self, request, context, change):
        return render_to_response(
            self.get_template(request, 'form'),
            context)

    # VIEWS

    def list_view(self, request):
        return self.render_list(request, {
            self.template_object_list_name: self.get_queryset(request),
            })

    def detail_view(self, request, object_pk):
        obj = self.get_object(request, object_pk)

        if not obj:
            raise Http404

        return self.render_detail(request, {
            self.template_object_name: obj,
            })

    def add_view(self, request):
        ModelForm = self.get_form(request)

        opts = self.model._meta

        if request.method == 'POST':
            form = ModelForm(request.POST, request.FILES)

            if form.is_valid():
                new_object = self.save_form(request, form, change=False)
                form_validated = True
            else:
                new_object = self.model()
                form_validated = False

            # TODO create and validate formsets (with instance=new_object)
            if all_valid([]) and form_validated:
                self.save_model(request, new_object, form, change=False)
                form.save_m2m()
                for formset in []:
                    self.save_formset(request, form, formset, change=False)

                return response_add(request, new_object)
        else:
            form = ModelForm()

        context = {
            'title': _('Add %s') % force_unicode(opts.verbose_name),
            'form': form,
            }

        return self.render_form(request, context, change=False)

    def response_add(request, new_object):
        self.message(request, _('The new object has been successfully created.'))
        return HttpResponseRedirect(new_object.get_absolute_url())

    def edit_view(self, request, object_pk):
        pass

    def delete_view(self, request, object_pk):
        pass

