from __future__ import absolute_import, unicode_literals

from django import forms
from django.contrib import messages
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import transaction
from django.forms.formsets import all_valid
from django.forms.models import modelform_factory, inlineformset_factory
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.utils import six
from django.utils.encoding import force_text
from django.utils.text import capfirst
from django.utils.translation import ugettext_lazy as _, ugettext

from towel import deletion, paginator
from towel.forms import towel_formfield_callback
from towel.utils import (
    app_model_label, related_classes, safe_queryset_and, tryreverse)

try:
    from django.urls import NoReverseMatch, reverse
except ImportError:
    from django.core.urlresolvers import NoReverseMatch, reverse


class ModelView(object):
    """
    ``ModelView`` offers list views, detail views and CRUD functionality
    """

    # Every view is wrapped with this decorator. Use this if you need
    # f.e. a simple way of ensuring a user is logged in before accessing
    # any view here.
    def view_decorator(self, func):
        """
        Returns the function as-is, does not apply permission checking or
        anything.
        """
        return func

    def crud_view_decorator(self, func):
        """
        Does what ``view_decorator`` above does (which is returning the passed
        view without applying any permission checking or anything).
        """
        return self.view_decorator(func)

    #: Used for detail and edit views
    template_object_name = 'object'

    #: Used for list views
    template_object_list_name = 'object_list'

    #: The base template which all default modelview templates inherit
    #: from
    base_template = 'base.html'

    #: The regular expression for detail URLs. Override this if you
    #: do not want the primary key in the URL.
    urlconf_detail_re = r'(?P<pk>\d+)'

    #: Paginate list views by this much. ``None`` means no pagination (the
    #: default).
    paginate_by = None

    #: By default, showing all objects on one page is allowed
    pagination_all_allowed = True

    #: The paginator class used for pagination
    paginator_class = paginator.Paginator

    #: The editing form class
    form_class = None

    #: Inline formsets. The key is the formset prefix and the formsets dict
    #: key at the same time, the value should be a dict instance which is
    #: used for the inlineformset_factory invocation.
    #:
    #: Example::
    #:
    #:     inlineformset_config = {
    #:         'steps': {'model': Step, 'form': CustomizedStepForm},
    #:         }
    #:
    inlineformset_config = {}

    #: Search form class
    search_form = None

    #: Search form is not only shown on list pages
    search_form_everywhere = False

    #: The form used for batch processing
    batch_form = None

    #: Messages dictionary to centrally control all possible messages
    default_messages = {
        'object_created': (
            messages.SUCCESS,
            _('The new object has been successfully created.')),
        'adding_denied': (
            messages.ERROR,
            _('You are not allowed to add objects.')),
        'object_updated': (
            messages.SUCCESS,
            _('The object has been successfully updated.')),
        'editing_denied': (
            messages.ERROR,
            _('You are not allowed to edit this object.')),
        'object_deleted': (
            messages.SUCCESS,
            _('The object has been successfully deleted.')),
        'deletion_denied': (
            messages.ERROR,
            _('You are not allowed to delete this object.')),
        'deletion_denied_related': (
            messages.ERROR,
            _('Deletion not allowed: There are %(pretty_classes)s related'
                ' to this object.')),
    }

    #: User defined messages
    custom_messages = {}

    def add_message(self, request, message, variables=None, level=None,
                    ignore=None, **kwargs):
        """
        This helper function is used to easily add messages for the current
        user.

        ``message`` may either be a key for the ``custom_messages`` and
        ``default_messages`` dictionary or a string containing the message
        itself.

        ``variables`` may be a dictionary used for string interpolation if the
        message contains placeholders.

        Some default messages already contain a message level specification
        (currently either ``SUCCESS`` or ``ERROR``). The default for all other
        messages is ``messages.INFO``, but this can be overridden by setting
        the ``level`` argument.

        If ``ignore`` is set to a list of message keys, all matching
        ``add_message`` calls during the current request-response cycle will
        be silently ignored.

        Additional keyword arguments are passed on directly to
        ``messages.add_message``. This can be used f.e. to easily add extra
        tags to the message.

        Usage::

            # Add the default object_created message
            self.add_message(request, 'object_created')

            # Add a custom message with a custom level
            self.add_message(request, _('Whatever you mean'),
                level=messages.WARNING)

            # Add extra tags to a default message
            self.add_message(request, 'deletion_denied', extra_tags='funky')

            # Fail loudly, please, if messages aren't enabled
            self.add_message(request, 'editing_denied', fail_silently=False)
        """

        message = force_text(message)

        ignorable = getattr(request, '_towel_add_message_ignore', [])
        if message in ignorable:
            return
        if ignore is not None:
            request._towel_add_message_ignore = ignore

        if message in self.custom_messages:
            message = self.custom_messages[message]
        elif message in self.default_messages:
            message = self.default_messages[message]

        if not isinstance(message, six.string_types):
            level = message[0]
            message = message[1]

        if variables:
            message = message % variables

        if level is None:
            level = messages.INFO

        # We should not fail if the messages framework is disabled
        kwargs.setdefault('fail_silently', True)

        messages.add_message(request, level, message, **kwargs)

    def __init__(self, model, **kwargs):
        self.model = model
        for key, value in kwargs.items():
            if not hasattr(self, key):
                raise TypeError('%s() received an invalid keyword %r' % (
                    self.__class__.__name__, key))
            setattr(self, key, value)

        if not hasattr(self.model, 'get_absolute_url'):
            # Add a simple primary key based URL to the model if it does not
            # have one yet
            self.model.get_absolute_url = lambda self: reverse(
                '%s_%s_detail' % app_model_label(self),
                args=(self.pk,),
            )

    def get_query_set(self, request, *args, **kwargs):
        """
        The queryset returned here is used for everything. Override this
        method if you want to show only a subset of objects to the current
        visitor.
        """
        return self.model._default_manager.all()

    def get_template(self, request, action):
        """
        Construct and return a template name for the given action.

        Example::

            self.get_template(request, 'list')

        returns the following template names for ``auth.User``::

            [
                'auth/user_list.html',
                'modelview/object_list.html',
            ]
        """
        return [
            '%s/%s_%s.html' % (app_model_label(self.model) + (action,)),
            'modelview/object_%s.html' % action,
        ]

    def get_urls(self):
        """
        Return all URLs known to this ``ModelView``. You probably do not
        need to override this except if you need more granular view
        decoration than offered with ``view_decorator`` and
        ``crud_view_decorator``. If you need additional URLs, use
        ``additional_urls`` instead.
        """
        from django.conf.urls import url
        info = app_model_label(self.model)

        urlpatterns = [
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
        ]

        for spec in self.additional_urls():
            urlp, view = spec[:2]
            if len(spec) > 2:
                ident = spec[2]
            else:
                ident = view.__name__

            urlpatterns.extend([
                url(
                    urlp % {
                        'detail': self.urlconf_detail_re,
                        'ident': ident,
                    },
                    view,
                    name=('%s_%s_%%s' % info) % ident
                ),
            ])

        urlpatterns.append(
            url(r'^%s/$' % self.urlconf_detail_re,
                self.view_decorator(self.detail_view),
                name='%s_%s_detail' % info),
        )

        return urlpatterns

    def additional_urls(self):
        """
        Define additional URLs for the modelview.

        You are responsible yourself for wrapping the views with permission
        decorators etc.

        The following example will add three views; %(detail)s is replaced with
        the regular expression ``urlconf_detail_re``. The URL pattern name is
        determined by ``<app_label>_<model_name>_<ident>``, where ``ident`` is
        either the third argument in the URL specification or the function name
        of the passed view::

            return [
                (r'^autocomplete/$',
                    self.view_decorator(self.autocomplete)),
                (r'^%(detail)s/statistics/$',
                    self.view_decorator(self.statistics), 'anything'),
                (r'^%(detail)s/something/$',
                    self.crud_view_decorator(self.something), 'something'),
                ]
        """

        return ()

    @property
    def urls(self):
        """
        Property returning the return value of ``get_urls``. Should
        be used inside the URLconf::

            from towel.modelview import ModelView

            urlpatterns = [
                url(r'^prefix/', include(ModelView(Model).urls)),
            ]
        """
        return self.get_urls()

    # HELPERS

    def get_object(self, request, *args, **kwargs):
        """
        Return an instance, raising ``DoesNotExist`` if an error occurs.

        The default implementation simply passes ``*args`` and
        ``**kwargs`` into ``queryset.get``.
        """
        queryset = self.get_query_set(request, *args, **kwargs)

        try:
            return queryset.get(*args, **kwargs)
        except (ValueError, ValidationError):
            raise self.model.DoesNotExist('No %s matches the given query.' % (
                self.model._meta.object_name))

    def get_object_or_404(self, request, *args, **kwargs):
        """
        Return an instance, raising a 404 if it could not be found.
        """
        try:
            return self.get_object(request, *args, **kwargs)
        except self.model.DoesNotExist:
            raise Http404('No %s matches the given query.' % (
                self.model._meta.object_name))

    def get_formfield_callback(self, request):
        """
        Returns a formfield callback used to initialize the model form and
        inline formsets.
        """
        return towel_formfield_callback

    def get_form(self, request, instance=None, change=None, **kwargs):
        """
        Return a form class for further use by add and edit views.

        Override this if you want to specify your own form class used
        for creating and editing objects.
        """

        kwargs.setdefault(
            'formfield_callback', self.get_formfield_callback(request))
        kwargs.setdefault('form', self.form_class or forms.ModelForm)
        kwargs.setdefault('exclude', ())

        return modelform_factory(self.model, **kwargs)

    def extend_args_if_post(self, request, args):
        """
        Helper which prepends POST and FILES to args if request method
        was POST. Ugly and helpful::

            args = self.extend_args_if_post(request, [])
            form = Form(*args, **kwargs)
        """

        if request.method == 'POST':
            args[:0] = [request.POST, request.FILES]

        return args

    def get_form_instance(self, request, form_class, instance=None,
                          change=None, **kwargs):
        """
        Returns the form instance

        Override this if your form class has special needs for instantiation.
        """
        args = self.extend_args_if_post(request, [])
        kwargs['instance'] = instance

        return form_class(*args, **kwargs)

    def get_formset_instances(self, request, instance=None, change=None,
                              **kwargs):
        """
        Return a dict of formset instances. You may freely choose the
        keys for this dict, use a SortedDict or something else as long
        as it has a 'values()' method.

        Please note that the instance passed here has not necessarily
        been saved to the database yet.
        """
        args = self.extend_args_if_post(request, [])
        kwargs['instance'] = instance

        formsets = {}

        formfield_callback = self.get_formfield_callback(request)

        for prefix, config in self.inlineformset_config.items():
            config.setdefault('form', forms.ModelForm)
            config.setdefault('formfield_callback', formfield_callback)
            config.setdefault('fields', '__all__')

            cls = inlineformset_factory(self.model, extra=0, **config)
            formsets[prefix] = cls(prefix=prefix, *args, **kwargs)

        return formsets

    def get_deletion_form_instance(self, request, instance, **kwargs):
        """
        Returns a form instance which can be used to ask additional
        questions about the deletion before it actually takes place.

        Defaults to an empty form which only verifies that the deletion
        request has been POSTed.
        """
        if request.method == 'POST':
            return forms.Form(request.POST, request.FILES)
        return forms.Form()

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
        """
        Loop over all formsets, calling ``save_formset`` for each.
        """
        for formset in formsets.values():
            self.save_formset(request, form, formset, change)

    def save_formset(self, request, form, formset, change):
        """
        Save an individual formset
        """
        formset.save()

    def post_save(self, request, instance, form, formsets, change):
        """
        Hook for adding custom processing after forms, m2m relations
        and formsets have been saved.
        """

        pass

    # VIEW HELPERS

    def get_extra_context(self, request):
        """
        Returns a context containing the following useful variables:

        * ``verbose_name``
        * ``verbose_name_plural``
        * ``list_url``
        * ``add_url``
        * ``base_template``
        * ``adding_allowed``
        * ``search_form`` (if ``search_form_everywhere = True``)
        """
        info = app_model_label(self.model)

        return {
            'verbose_name': self.model._meta.verbose_name,
            'verbose_name_plural': self.model._meta.verbose_name_plural,
            'list_url': tryreverse('%s_%s_list' % info),
            'add_url': tryreverse('%s_%s_add' % info),
            'base_template': self.base_template,

            'adding_allowed': self.adding_allowed(request),

            'search_form': (
                self.search_form(request.GET, request=request)
                if self.search_form_everywhere else None),

            'request': request,  # Something changed with Django 1.10's
                                 # context processors...
        }

    def get_context(self, request, context):
        """
        Return a context dictionary which also contains everything from
        ``get_extra_context``.
        """
        ctx = self.get_extra_context(request)
        ctx.update(context)
        return ctx

    def render(self, request, template, context):
        """
        Render the whole shebang.
        """
        return render(request, template, context)

    def render_list(self, request, context):
        """
        Render the list view
        """
        return self.render(
            request,
            self.get_template(request, 'list'),
            self.get_context(request, context))

    def render_detail(self, request, context):
        """
        Render the detail view
        """
        return self.render(
            request,
            self.get_template(request, 'detail'),
            self.get_context(request, context))

    def render_form(self, request, context, change):
        """
        Render the add and edit views
        """
        return self.render(
            request,
            self.get_template(request, 'form'),
            self.get_context(request, context))

    def render_delete_confirmation(self, request, context):
        """
        Render the deletion confirmation page
        """
        return self.render(
            request,
            self.get_template(request, 'delete_confirmation'),
            self.get_context(request, context))

    def response_add(self, request, instance, form, formsets):
        """
        Return the response after successful addition of a new instance
        """
        self.add_message(request, 'object_created')

        if '_continue' in request.POST:
            return HttpResponseRedirect(instance.get_absolute_url() + 'edit/')

        return redirect(instance)

    def response_adding_denied(self, request):
        """
        Return the response when adding instances is denied
        """
        self.add_message(request, 'adding_denied')
        url = tryreverse('%s_%s_list' % app_model_label(self.model))
        return HttpResponseRedirect(url if url else '../../')

    def response_edit(self, request, instance, form, formsets):
        """
        Return the response after an instance has been successfully edited
        """
        self.add_message(request, 'object_updated')

        if '_continue' in request.POST:
            return HttpResponseRedirect('.')

        return redirect(instance)

    def response_editing_denied(self, request, instance):
        """
        Return the response when editing the given instance is denied
        """
        self.add_message(request, 'editing_denied')
        return redirect(instance)

    def response_delete(self, request, instance):
        """
        Return the response when an object has been successfully deleted
        """
        self.add_message(request, 'object_deleted')
        url = tryreverse('%s_%s_list' % app_model_label(self.model))
        return HttpResponseRedirect(url if url else '../../')

    def response_deletion_denied(self, request, instance):
        """
        Return the response when deleting the given instance is not allowed
        """
        self.add_message(request, 'deletion_denied')
        return redirect(instance)

    def paginate_object_list(self, request, queryset, paginate_by=10):
        """
        Helper which paginates the given object list

        Skips pagination if the magic ``all`` GET parameter is set.
        """
        paginator_obj = self.paginator_class(queryset, paginate_by)

        try:
            page = int(request.GET.get('page', '1'))
        except ValueError:
            page = 1

        try:
            page_obj = paginator_obj.page(page)
        except (paginator.EmptyPage, paginator.InvalidPage):
            page_obj = paginator_obj.page(paginator_obj.num_pages)

        if self.pagination_all_allowed and request.GET.get('all'):
            page_obj.object_list = queryset
            page_obj.show_all_objects = True
            page_obj.start_index = 1
            page_obj.end_index = paginator_obj.count

        return page_obj, paginator_obj

    # VIEWS

    def list_view(self, request, *args, **kwargs):
        """
        Handles the listing of objects

        This view knows how to paginate objects and is able
        to handle search and batch forms, too.
        """
        ctx = {}
        queryset = self.get_query_set(request, *args, **kwargs)
        ctx['root_%s' % self.template_object_list_name] = queryset

        queryset, response = self.handle_search_form(request, ctx, queryset)

        if response:
            return response

        response = self.handle_batch_form(request, ctx, queryset)
        if response:
            return response

        ctx['full_%s' % self.template_object_list_name] = queryset

        if self.paginate_by:
            page, paginator = self.paginate_object_list(
                request, queryset, self.paginate_by)

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
        Must return a tuple consisting of a queryset and either a HttpResponse
        or ``None``
        """

        if queryset is None:
            queryset = self.get_query_set(request)

        if self.search_form:
            form = self.search_form(request.GET, request=request)
            if not form.is_valid():
                self.add_message(
                    request,
                    _('The search query was invalid.'),
                    level=messages.ERROR)

                if request.get_full_path().endswith('?clear=1'):
                    # No redirect loop generation
                    raise ImproperlyConfigured(
                        'Search form %r does not validate after'
                        ' clearing.' % form)

                return queryset, HttpResponseRedirect('?clear=1')

            queryset = safe_queryset_and(queryset, form.queryset(self.model))

            ctx['search_form'] = form

        return queryset, None

    def handle_batch_form(self, request, ctx, queryset):
        """
        May optionally return a HttpResponse which is directly returned to the
        browser
        """

        if not self.batch_form:
            return

        form = self.batch_form(request, queryset)
        ctx['batch_form'] = form

        if form.should_process():
            result = form.process()

            if isinstance(result, HttpResponse):
                return result

            elif hasattr(result, '__iter__'):
                messages.success(
                    request,
                    _('Processed the following items: <br>\n %s') % (
                        '<br>\n '.join(
                            force_text(item) for item in result)))

            elif result is not None:
                # Not None, but cannot make sense of it either.
                raise TypeError('Return value %r of %s.process() invalid.' % (
                    result,
                    form.__class__.__name__,
                ))

            url = tryreverse('%s_%s_list' % app_model_label(self.model))
            return HttpResponseRedirect(url if url else '.')

    def detail_view(self, request, *args, **kwargs):
        """
        Simple detail page view
        """
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

    def process_form(self, request, instance=None, change=None):
        """
        Processes forms, used by ``add_view`` and ``edit_view``
        """

        new_instance = None
        valid = False
        ModelForm = self.get_form(request, instance, change=change)

        if request.method == 'POST':
            form = self.get_form_instance(
                request, ModelForm, instance=instance, change=change)

            if form.is_valid():
                new_instance = self.save_form(request, form, change=change)
                form_validated = True
            else:
                new_instance = self.model() if instance is None else instance
                form_validated = False

            formsets = self.get_formset_instances(
                request, instance=new_instance, change=change)

            if all_valid(formsets.values()) and form_validated:
                with transaction.atomic():
                    self.save_model(request, new_instance, form, change=change)
                    form.save_m2m()
                    self.save_formsets(request, form, formsets, change=change)
                    self.post_save(
                        request, new_instance, form, formsets, change=change)

                valid = True
        else:
            form = self.get_form_instance(
                request, ModelForm, instance=instance, change=change)
            formsets = self.get_formset_instances(
                request, instance=instance, change=change)

        return form, formsets, new_instance, valid

    def add_view(self, request):
        """
        Add view with some additional formset handling
        """
        if not self.adding_allowed(request):
            return self.response_adding_denied(request)

        form, formsets, new_instance, valid = self.process_form(
            request, change=False)

        if valid:
            return self.response_add(request, new_instance, form, formsets)

        opts = self.model._meta

        context = {
            'title': capfirst(_('Add %s') % force_text(opts.verbose_name)),
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
        """
        Edit view with some additional formset handling
        """
        instance = self.get_object_or_404(request, *args, **kwargs)

        if not self.editing_allowed(request, instance):
            return self.response_editing_denied(request, instance)

        form, formsets, new_instance, valid = self.process_form(
            request, instance=instance, change=True)

        if valid:
            return self.response_edit(request, new_instance, form, formsets)

        opts = self.model._meta

        context = {
            'title': capfirst(
                _('Change %s') % force_text(opts.verbose_name)),
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
        """
        Helper which is most useful when used inside ``deletion_allowed``

        Allows the deletion if the deletion cascade only contains
        objects from the given classes. Adds a message if deletion is
        not allowed containing details which classes are preventing
        deletion.

        Example::

            def deletion_allowed(self, request, instance):
                return self.deletion_allowed_if_only(request, instance, [
                    Ticket, TicketUpdate])
        """
        related = set(related_classes(instance))

        related.discard(self.model)
        for class_ in classes:
            related.discard(class_)

        if len(related):
            pretty_classes = [
                force_text(class_._meta.verbose_name_plural)
                for class_ in related]

            if len(pretty_classes) > 1:
                pretty_classes = ''.join((
                    ', '.join('%s' % cls for cls in pretty_classes[:-1]),
                    ugettext(' and '),
                    '%s' % pretty_classes[-1],
                ))
            else:
                pretty_classes = pretty_classes[-1]

            self.add_message(
                request,
                'deletion_denied_related',
                {'pretty_classes': pretty_classes},
                ignore=('deletion_denied',),
            )

        return not len(related)

    def save_formset_deletion_allowed_if_only(self, request, form, formset,
                                              change, classes):
        """
        Helper which has is most useful when used inside ``save_formsets``

        To use this method properly, your model has to inherit from
        ``towel.deletion.Model``. This is NOT enforced. If you ignore this, the
        instances will be deleted by ``formset.save()`` as is the default with
        Django.

        Example::

            def save_formsets(self, requset, form, formsets, change):
                # Allow deleting states when the cascade includes
                # ``SomeModel`` instances only.
                self.save_formset_deletion_allowed_if_only(
                    request, form, formsets['states'], change, [SomeModel])

                # No special handling for other formsets
                self.save_formset(request, form, formsets['otherformset'],
                    change=change)

        """
        with deletion.protect():
            self.save_formset(request, form, formset, change)

        for instance in formset.deleted_objects:
            related = set(related_classes(instance))

            related.discard(instance.__class__)
            for class_ in classes:
                related.discard(class_)

            if len(related):
                pretty_classes = [
                    force_text(class_._meta.verbose_name_plural)
                    for class_ in related]

                if len(pretty_classes) > 1:
                    pretty_classes = ''.join((
                        ', '.join(pretty_classes[:-1]),
                        ugettext(' and '),
                        pretty_classes[-1],
                    ))
                else:
                    pretty_classes = pretty_classes[-1]

                self.add_message(request, 'deletion_denied_related', {
                    'pretty_classes': pretty_classes})
            else:
                instance.delete()

    def delete_view(self, request, *args, **kwargs):
        """
        Handles deletion
        """
        obj = self.get_object_or_404(request, *args, **kwargs)

        if not self.deletion_allowed(request, obj):
            return self.response_deletion_denied(request, obj)

        form = self.get_deletion_form_instance(request, obj)

        if form.is_valid():
            obj.delete()
            return self.response_delete(request, obj)
        else:
            if not hasattr(obj, '_collected_objects'):
                related_classes(obj)

            collected_objects = [
                (key._meta, len(value))
                for key, value in obj._collected_objects.items()]

            return self.render_delete_confirmation(request, {
                'title': capfirst(_('Delete %s') % force_text(
                    self.model._meta.verbose_name)),
                self.template_object_name: obj,
                'collected_objects': collected_objects,
                'form': form,
            })


class _MVUHelper(object):
    def __init__(self, viewname_pattern, kwargs):
        self.viewname_pattern = viewname_pattern
        self.kwargs = kwargs

    def __getitem__(self, item):
        return self.url(item)

    def url(self, item, *args, **kwargs):
        kw = self.kwargs.copy()
        if args:
            kw.setdefault('args', [])
            kw['args'].extend(args)
        elif kwargs:
            kw.setdefault('kwargs', {})
            kw['kwargs'].update(kwargs)

        try:
            return reverse(self.viewname_pattern % item, **kw)
        except NoReverseMatch as e:
            try:
                return reverse(self.viewname_pattern % item)
            except NoReverseMatch:
                # Re-raise exception with kwargs; it's more informative
                raise e


class ModelViewURLs(object):
    """
    Usage::

        class MyModel(models.Model):
            urls = ModelViewURLs(lambda obj: {'pk': obj.pk})

            def get_absolute_url(self):
                return self.urls['detail']

            def get_edit_url(self):
                return self.urls['edit']

            # ... etc
    """

    def __init__(self, reverse_args_fn=None):
        """
        Despite the name, ``reverse_args_fn`` is allowed to return kwargs
        (a dict instance) too
        """
        if reverse_args_fn:
            self.reverse_args_fn = reverse_args_fn
        else:
            self.reverse_args_fn = lambda obj: {'pk': obj.pk}

    def __get__(self, obj, objtype=None):
        if not hasattr(obj, '_modelviewurls_cache'):
            kwargs = {}
            data = self.reverse_args_fn(obj)
            if isinstance(data, dict):
                kwargs['kwargs'] = data
            else:
                kwargs['args'] = data

            viewname_pattern = '%s_%s_%%s' % app_model_label(obj)

            obj._modelviewurls_cache = _MVUHelper(viewname_pattern, kwargs)
        return obj._modelviewurls_cache
