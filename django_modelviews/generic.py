import datetime
import decimal
import urllib

from django.contrib import messages
from django.core import paginator
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models
from django.forms.formsets import all_valid
from django.forms.models import modelform_factory
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render_to_response
from django.template import RequestContext
from django.utils.encoding import force_unicode
from django.utils.translation import ugettext as _


class ModelView(object):
    # Every view is wrapped with this decorator. Use this if you need
    # f.e. a simple way of ensuring a user is logged in before accessing
    # any view here.
    view_decorator = lambda self, f: f
    crud_view_decorator = None

    # Used for detail and edit views
    template_object_name = 'object'

    # Used for list views
    template_object_list_name = 'object_list'

    urlconf_detail_re = r'(?P<pk>\d+)'

    def __init__(self, model, **kwargs):
        self.model = model
        for k, v in kwargs.items():
            setattr(self, k, v)

        if not hasattr(self.model, 'get_absolute_url'):
            # Add a simple primary key based URL to the model if it does not have one yet
            info = self.model._meta.app_label, self.model._meta.module_name
            self.model.get_absolute_url = models.permalink(lambda self: (
                '%s_%s_detail' % info, (self.pk,), {}))

    def get_query_set(self, request):
        return self.model.objects.all()

    def get_template(self, request, action):
        """
        Construct and return a template name for the given action.
        """

        opts = self.model._meta
        return [
            '%s/%s_%s.html' % (opts.app_label, opts.module_name, action),
            'modelview/object_%s.html' % action,
            ]

    def get_urls(self):
        from django.conf.urls.defaults import patterns, url
        info = self.model._meta.app_label, self.model._meta.module_name

        if not self.crud_view_decorator:
            self.crud_view_decorator = self.view_decorator

        return patterns('',
            url(r'^$',
                self.view_decorator(self.list_view),
                name='%s_%s_list' % info),
            url(r'^add/$',
                self.crud_view_decorator(self.add_view),
                name='%s_%s_add' % info),
            url(r'^%s/edit/$' % self.urlconf_detail_re,
                self.crud_view_decorator(self.edit_view),
                name='%s_%s_edit' % info),
            url(r'^%s/delete/$' % self.urlconf_detail_re,
                self.crud_view_decorator(self.delete_view),
                name='%s_%s_delete' % info),
            url(r'^%s/$' % self.urlconf_detail_re,
                self.view_decorator(self.detail_view),
                name='%s_%s_detail' % info),
            )

    @property
    def urls(self):
        return self.get_urls()

    # HELPERS

    def get_object(self, request, **kwargs):
        queryset = self.get_query_set(request)
        model = queryset.model

        try:
            return queryset.get(**kwargs)
        except (model.DoesNotExist, ValueError, ValidationError):
            raise self.model.DoesNotExist

    def get_object_or_404(self, request, **kwargs):
        try:
            return self.get_object(request, **kwargs)
        except self.model.DoesNotExist:
            raise Http404

    def get_form(self, request, instance=None, **kwargs):
        """
        Return a form class for further use by add and edit views.
        """

        return modelform_factory(self.model, **kwargs)

    def extend_args_if_post(self, request, args):
        """
        Helper which prepends POST and FILES to args if request method
        was POST.
        """

        if request.method == 'POST':
            args[:0] = [request.POST, request.FILES]

        return args

    def get_form_instance(self, request, form_class, instance=None, **kwargs):
        args = self.extend_args_if_post(request, [])
        kwargs['instance'] = instance

        return form_class(*args, **kwargs)

    def get_formset_instances(self, request, instance=None, **kwargs):
        """
        Return a dict of formset instances. You may freely choose the
        keys for this dict, use a SortedDict or something else as long
        as it has a 'itervalues()' method.

        Please note that the instance passed here has not necessarily
        been saved to the database yet.
        """

        return {}

    def message(self, request, message):
        messages.info(request, message)

    def save_form(self, request, form, change):
        """
        Return an unsaved instance when editing an object.
        """

        return form.save(commit=False)

    def save_model(self, request, instance, form, change):
        """
        Save an object to the database.
        """

        instance.save()

    def save_formset(self, request, form, formset, change):
        formset.save()

    # VIEW HELPERS

    def get_extra_context(self, request):
        from django.core.urlresolvers import reverse
        info = self.model._meta.app_label, self.model._meta.module_name

        return {
            'verbose_name': self.model._meta.verbose_name,
            'verbose_name_plural': self.model._meta.verbose_name_plural,
            'list_url': reverse('%s_%s_list' % info),
            'add_url': reverse('%s_%s_add' % info),
        }

    def get_context(self, request, context):
        instance = RequestContext(request, self.get_extra_context(request))
        instance.update(context)
        return instance

    def render_list(self, request, context):
        return render_to_response(
            self.get_template(request, 'list'),
            self.get_context(request, context))

    def render_detail(self, request, context):
        return render_to_response(
            self.get_template(request, 'detail'),
            self.get_context(request, context))

    def render_form(self, request, context, change):
        return render_to_response(
            self.get_template(request, 'form'),
            self.get_context(request, context))

    def response_add(self, request, instance, form, formsets):
        self.message(request, _('The new object has been successfully created.'))
        return redirect(instance)

    def response_edit(self, request, instance, form, formsets):
        self.message(request, _('The object has been successfully updated.'))
        return redirect(instance)

    def paginate_object_list(self, request, queryset, paginate_by=10):
        paginator_obj = paginator.Paginator(queryset, paginate_by)

        try:
            page = int(request.GET.get('page', '1'))
        except ValueError:
            page = 1

        try:
            return paginator_obj.page(page)
        except (paginator.EmptyPage, paginator.InvalidPage):
            return paginator_obj.page(paginator_obj.num_pages)

    # VIEWS

    def list_view(self, request):
        return self.render_list(request, {
            self.template_object_list_name: self.get_query_set(request),
            })

    def detail_view(self, request, object_pk):
        instance = self.get_object_or_404(request, pk=object_pk)

        return self.render_detail(request, {
            self.template_object_name: instance,
            })

    def add_view(self, request):
        ModelForm = self.get_form(request)

        opts = self.model._meta

        if request.method == 'POST':
            form = self.get_form_instance(request, ModelForm)

            if form.is_valid():
                new_instance = self.save_form(request, form, change=False)
                form_validated = True
            else:
                new_instance = self.model()
                form_validated = False

            formsets = self.get_formset_instances(request, instance=new_instance)
            if all_valid(formsets.itervalues()) and form_validated:
                self.save_model(request, new_instance, form, change=False)
                form.save_m2m()
                for formset in formsets.itervalues():
                    self.save_formset(request, form, formset, change=False)

                return self.response_add(request, new_instance, form, formsets)
        else:
            form = self.get_form_instance(request, ModelForm)
            formsets = self.get_formset_instances(request)

        context = {
            'title': _('Add %s') % force_unicode(opts.verbose_name),
            'form': form,
            'formsets': formsets,
            }

        return self.render_form(request, context, change=False)

    def edit_view(self, request, object_pk):
        instance = self.get_object_or_404(request, pk=object_pk)
        ModelForm = self.get_form(request, instance)

        opts = self.model._meta

        if request.method == 'POST':
            form = self.get_form_instance(request, ModelForm, instance)

            if form.is_valid():
                new_instance = self.save_form(request, form, change=True)
                form_validated = True
            else:
                new_instance = instance
                form_validated = False

            formsets = self.get_formset_instances(request, instance=new_instance)
            if all_valid(formsets.itervalues()) and form_validated:
                self.save_model(request, new_instance, form, change=True)
                form.save_m2m()
                for formset in formsets.itervalues():
                    self.save_formset(request, form, formset, change=False)

                return self.response_edit(request, new_instance, form, formsets)
        else:
            form = self.get_form_instance(request, ModelForm, instance)
            formsets = self.get_formset_instances(request, instance=instance)

        context = {
            'title': _('Change %s') % force_unicode(opts.verbose_name),
            'form': form,
            'formsets': formsets,
            self.template_object_name: instance,
            }

        return self.render_form(request, context, change=True)

    def deletion_allowed(self, request, instance):
        """
        By default, deletion is not allowed.
        """

        return False

    def delete_view(self, request, object_pk):
        obj = self.get_object_or_404(request, pk=object_pk)

        if self.deletion_allowed(request, obj):
            obj.delete()
            self.message(request, _('The object has been successfully deleted.'))

            info = self.model._meta.app_label, self.model._meta.module_name
            return redirect('%s_%s_list' % info)
        else:
            self.message(request, _('You are not allowed to delete this object.'))
            return redirect(obj)


def querystring(data):
    def _v(v):
        if isinstance(v, models.Model):
            return v.pk
        elif isinstance(v, bool):
            return v and 1 or ''
        elif isinstance(v, datetime.date):
            return v.strftime('%Y-%m-%d')
        elif isinstance(v, decimal.Decimal):
            return str(v)
        return v.encode('utf-8')

    values = []

    try:
        # Handle MultiValueDicts
        items = data.lists()
    except AttributeError:
        items = data.items()

    for k, v in items:
        if v is None:
            continue

        if isinstance(v, list):
            for v2 in v:
                values.append((k, _v(v2)))
        else:
            values.append((k, _v(v)))

    return urllib.urlencode(values)
