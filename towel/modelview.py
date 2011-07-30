import datetime
import decimal
import urllib

from django.contrib import messages
from django.core import paginator
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.urlresolvers import reverse, NoReverseMatch
from django.db import models
from django.db.models.deletion import Collector
from django.forms.formsets import all_valid
from django.forms.models import modelform_factory
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render_to_response
from django.template import RequestContext
from django.utils.encoding import force_unicode
from django.utils.translation import ugettext as _


def _tryreverse(*args, **kwargs):
    try:
        return reverse(*args, **kwargs)
    except NoReverseMatch:
        return None


class ModelView(object):
    """``ModelView`` offers list views, detail views and CRUD functionality"""

    # Every view is wrapped with this decorator. Use this if you need
    # f.e. a simple way of ensuring a user is logged in before accessing
    # any view here.
    def view_decorator(self, func):
        return func
    def crud_view_decorator(self, func):
        return self.view_decorator(func)

    # Used for detail and edit views
    template_object_name = 'object'

    # Used for list views
    template_object_list_name = 'object_list'

    base_template = 'base.html'

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

    def get_query_set(self, request, *args, **kwargs):
        return self.model._default_manager.all()

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

        urlpatterns = patterns('',
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
            )

        for spec in self.additional_urls():
            urlp, view = spec[:2]
            if len(spec) > 2:
                ident = spec[2]
            else:
                ident = view.__name__

            urlpatterns += patterns('',
                url(urlp % {
                        'detail': self.urlconf_detail_re,
                        'ident': ident,
                        },
                    view,
                    name=('%s_%s_%%s' % info) % ident),
                )

        urlpatterns += patterns('',
            url(r'^%s/$' % self.urlconf_detail_re,
                self.view_decorator(self.detail_view),
                name='%s_%s_detail' % info),
            )

        return urlpatterns

    def additional_urls(self):
        """
        Define additional URLs for the modelview.

        You are responsible yourself for wrapping the views with permission decorators etc.

        The following example will add three views; %(detail)s is replaced with the
        regular expression ``urlconf_detail_re``. The URL pattern name is determined by
        ``<app_label>_<module_name>_<ident>``, where ``ident`` is either the third argument
        in the URL specification or the function name of the passed view::

            return [
                (r'^autocomplete/$', self.view_decorator(self.autocomplete)),
                (r'^%(detail)s/statistics/$', self.view_decorator(self.statistics), 'anything'),
                (r'^%(detail)s/something/$', self.crud_view_decorator(self.something), 'something'),
                ]
        """

        return ()

    @property
    def urls(self):
        return self.get_urls()

    # HELPERS

    def get_object(self, request, *args, **kwargs):
        queryset = self.get_query_set(request, *args, **kwargs)

        try:
            return queryset.get(*args, **kwargs)
        except (ValueError, ValidationError):
            raise self.model.DoesNotExist

    def get_object_or_404(self, request, *args, **kwargs):
        try:
            return self.get_object(request, *args, **kwargs)
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

    def get_form_instance(self, request, form_class, instance=None, change=None, **kwargs):
        args = self.extend_args_if_post(request, [])
        kwargs['instance'] = instance

        return form_class(*args, **kwargs)

    def get_formset_instances(self, request, instance=None, change=None, **kwargs):
        """
        Return a dict of formset instances. You may freely choose the
        keys for this dict, use a SortedDict or something else as long
        as it has a 'itervalues()' method.

        Please note that the instance passed here has not necessarily
        been saved to the database yet.
        """

        return {}

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

    def save_formsets(self, request, form, formsets, change):
        for formset in formsets.itervalues():
            self.save_formset(request, form, formset, change)

    def save_formset(self, request, form, formset, change):
        formset.save()

    def post_save(self, request, instance, form, formset, change):
        """
        Hook for adding custom processing after forms, m2m relations
        and formsets have been saved.
        """

        pass

    # VIEW HELPERS

    def get_extra_context(self, request):
        info = self.model._meta.app_label, self.model._meta.module_name

        return {
            'verbose_name': self.model._meta.verbose_name,
            'verbose_name_plural': self.model._meta.verbose_name_plural,
            'list_url': _tryreverse('%s_%s_list' % info),
            'add_url': _tryreverse('%s_%s_add' % info),
            'base_template': self.base_template,

            'adding_allowed': self.adding_allowed(request),
        }

    def get_context(self, request, context):
        instance = RequestContext(request, self.get_extra_context(request))
        instance.update(context)
        return instance

    def render(self, request, template, context):
        return render_to_response(template, context)

    def render_list(self, request, context):
        return self.render(request,
            self.get_template(request, 'list'),
            self.get_context(request, context))

    def render_detail(self, request, context):
        return self.render(request,
            self.get_template(request, 'detail'),
            self.get_context(request, context))

    def render_form(self, request, context, change):
        return self.render(request,
            self.get_template(request, 'form'),
            self.get_context(request, context))

    def render_delete_confirmation(self, request, context):
        return self.render(request,
            self.get_template(request, 'delete_confirmation'),
            self.get_context(request, context))

    def response_add(self, request, instance, form, formsets):
        messages.success(request, _('The new object has been successfully created.'))

        if '_continue' in request.POST:
            return HttpResponseRedirect(instance.get_absolute_url() + 'edit/')

        return redirect(instance)

    def response_adding_denied(self, request):
        messages.error(request, _('You are not allowed to add objects.'))
        info = self.model._meta.app_label, self.model._meta.module_name
        url = _tryreverse('%s_%s_list' % info)
        return HttpResponseRedirect(url if url else '../../')

    def response_edit(self, request, instance, form, formsets):
        messages.success(request, _('The object has been successfully updated.'))

        if '_continue' in request.POST:
            return HttpResponseRedirect('.')

        return redirect(instance)

    def response_editing_denied(self, request, instance):
        messages.error(request, _('You are not allowed to edit this object.'))
        return redirect(instance)

    def response_delete(self, request, instance):
        messages.success(request, _('The object has been successfully deleted.'))
        info = self.model._meta.app_label, self.model._meta.module_name
        url = _tryreverse('%s_%s_list' % info)
        return HttpResponseRedirect(url if url else '../../')

    def response_deletion_denied(self, request, instance):
        messages.error(request, _('You are not allowed to delete this object.'))
        return redirect(instance)

    def paginate_object_list(self, request, queryset, paginate_by=10):
        paginator_obj = paginator.Paginator(queryset, paginate_by)

        try:
            page = int(request.GET.get('page', '1'))
        except ValueError:
            page = 1

        try:
            page_obj = paginator_obj.page(page)
        except (paginator.EmptyPage, paginator.InvalidPage):
            page_obj = paginator_obj.page(paginator_obj.num_pages)

        if request.GET.get('all'):
            page_obj.object_list = queryset
            page_obj.show_all_objects = True

        return page_obj, paginator_obj

    # VIEWS

    def list_view(self, request, *args, **kwargs):
        paginate_by = getattr(self, 'paginate_by', None)

        ctx = {}

        queryset, response = self.handle_search_form(request, ctx,
            queryset=self.get_query_set(request, *args, **kwargs))

        if response:
            return response

        response = self.handle_batch_form(request, ctx, queryset)
        if response:
            return response

        ctx['full_%s' % self.template_object_list_name] = queryset

        if paginate_by:
            page, paginator = self.paginate_object_list(request, queryset, paginate_by)

            ctx.update({
                self.template_object_list_name: page.object_list,
                'page': page,
                'paginator': paginator,
                })
        else:
            ctx[self.template_object_list_name] = queryset

        return self.render_list(request, ctx)

    def handle_search_form(self, request, ctx, queryset=None):
        """
        Must return a tuple consisting of a queryset and either a HttpResponse or None
        """

        if queryset is None:
            queryset = self.get_query_set(request)

        search_form = getattr(self, 'search_form', None)
        if search_form:
            form = search_form(request.GET, request=request)
            queryset = safe_queryset_and(queryset, form.queryset(self.model))

            ctx['search_form'] = form

        return queryset, None

    def handle_batch_form(self, request, ctx, queryset):
        """
        May optionally return a HttpResponse which is directly returned to the browser
        """

        batch_form = getattr(self, 'batch_form', None)
        if batch_form:
            form = batch_form(request)
            ctx.update(form.context(queryset))

            if 'response' in ctx:
                return ctx['response']

    def detail_view(self, request, *args, **kwargs):
        instance = self.get_object_or_404(request, *args, **kwargs)

        return self.render_detail(request, {
            self.template_object_name: instance,
            'editing_allowed': self.editing_allowed(request, instance),
            })

    def adding_allowed(self, request):
        """
        By default, adding is allowed.
        """

        return True

    def add_view(self, request):
        if not self.adding_allowed(request):
            return self.response_adding_denied(request)

        ModelForm = self.get_form(request)

        opts = self.model._meta

        if request.method == 'POST':
            form = self.get_form_instance(request, ModelForm, change=False)

            if form.is_valid():
                new_instance = self.save_form(request, form, change=False)
                form_validated = True
            else:
                new_instance = self.model()
                form_validated = False

            formsets = self.get_formset_instances(request, instance=new_instance, change=False)
            if all_valid(formsets.itervalues()) and form_validated:
                self.save_model(request, new_instance, form, change=False)
                form.save_m2m()
                self.save_formsets(request, form, formsets, change=False)
                self.post_save(request, new_instance, form, formsets, change=False)

                return self.response_add(request, new_instance, form, formsets)
        else:
            form = self.get_form_instance(request, ModelForm, change=False)
            formsets = self.get_formset_instances(request, change=False)

        context = {
            'title': _('Add %s') % force_unicode(opts.verbose_name),
            'form': form,
            'formsets': formsets,
            }

        return self.render_form(request, context, change=False)

    def editing_allowed(self, request, instance):
        """
        By default, editing is allowed.
        """

        return True

    def edit_view(self, request, *args, **kwargs):
        instance = self.get_object_or_404(request, *args, **kwargs)

        if not self.editing_allowed(request, instance):
            return self.response_editing_denied(request, instance)

        ModelForm = self.get_form(request, instance)

        opts = self.model._meta

        if request.method == 'POST':
            form = self.get_form_instance(request, ModelForm, instance, change=True)

            if form.is_valid():
                new_instance = self.save_form(request, form, change=True)
                form_validated = True
            else:
                new_instance = instance
                form_validated = False

            formsets = self.get_formset_instances(request, instance=new_instance, change=True)
            if all_valid(formsets.itervalues()) and form_validated:
                self.save_model(request, new_instance, form, change=True)
                form.save_m2m()
                self.save_formsets(request, form, formsets, change=True)
                self.post_save(request, new_instance, form, formsets, change=True)

                return self.response_edit(request, new_instance, form, formsets)
        else:
            form = self.get_form_instance(request, ModelForm, instance, change=True)
            formsets = self.get_formset_instances(request, instance=instance, change=True)

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

    def deletion_allowed_if_only(self, request, instance, classes):
        related = set(related_classes(instance))

        related.discard(self.model)
        for class_ in classes:
            related.discard(class_)

        if len(related):
            pretty_classes = [unicode(class_._meta.verbose_name_plural) for class_ in related]
            if len(pretty_classes) > 1:
                pretty_classes = u''.join((
                    u', '.join(pretty_classes[:-1]),
                    _(' and '),
                    pretty_classes[-1]))
            else:
                pretty_classes = pretty_classes[-1]

            messages.error(request,
                _('Deletion not allowed: There are %s related to this object.') % pretty_classes)

        return not len(related)

    def delete_view(self, request, *args, **kwargs):
        obj = self.get_object_or_404(request, *args, **kwargs)

        if not self.deletion_allowed(request, obj):
            return self.response_deletion_denied(request, obj)

        if request.method == 'POST':
            obj.delete()
            return self.response_delete(request, obj)
        else:
            collected_objects = getattr(obj, '_collected_objects', None)

            if collected_objects:
                collected_objects = [(key._meta, len(value)) for key, value in collected_objects.items()]

            return self.render_delete_confirmation(request, {
                'title': _('Delete %s') % force_unicode(self.model._meta.verbose_name),
                self.template_object_name: obj,
                'collected_objects': collected_objects,
                })


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


def related_classes(instance):
    collector = Collector(using=instance._state.db)
    collector.collect([instance])

    # Save collected objects for later referencing
    instance._collected_objects = collector.data

    return collector.data.keys()


def deletion_allowed_if_only(instance, classes):
    related = set(related_classes(instance))

    related.discard(instance.__class__)
    for class_ in classes:
        related.discard(class_)

    return not len(related)


def safe_queryset_and(qs1, qs2):
    if qs1.query.distinct or qs2.query.distinct:
        return qs1.distinct() & qs2.distinct()
    return qs1 & qs2
