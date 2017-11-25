"""
This is an experiment in splitting up the monolithic model view class into
smaller, more reusable parts, and using class-based views at the same time
(not the generic class based views, though)

The basic idea is that creating a new instance for every request and having
different classes handling different types of requests (listing, details,
editing etc.) are both really good ideas. That's what Django's class-based
views do, and they do it quite well. However, sharing functionality between
those different classes is hard: Adding limits to querysets centrally, adding
a common set of list/detail/crud views, adding the same context variables to
all views for the same Django model are all harder than they should be.

That's where ``towel.resources`` really shines. All views inherit from
``ModelResourceView`` which in turn inherits all functionality of
``django.views.generic.base.TemplateView``. Many methods such as
``get_queryset``, ``get_context_data``, ``get_form_kwargs`` etc. are closely
modelled after the generic class-based views of Django itself, the inheritance
hierarchy is a lot simpler and we use less mixins, and less inversion of
control which should make code written with ``towel.resources`` easier to
understand and follow.

At least that's one of our goals here.
"""

from __future__ import absolute_import, unicode_literals

import json

from django import forms
from django.contrib import messages
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.forms.models import modelform_factory, model_to_dict
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.utils.encoding import force_text
from django.utils.text import capfirst
from django.utils.translation import ugettext as _
from django.views.generic.base import TemplateView

from towel.forms import BatchForm, towel_formfield_callback
from towel.paginator import Paginator, EmptyPage, InvalidPage
from towel.utils import (
    app_model_label, changed_regions, related_classes, safe_queryset_and)

try:
    from django.urls import NoReverseMatch
except ImportError:
    from django.core.urlresolvers import NoReverseMatch


class ModelResourceView(TemplateView):
    """
    This is the base class of all views in ``towel.resources``.
    """

    #: The ``base_template`` variable is passed into the template context
    #: when rendering any templates. It's most useful when adding a base
    #: template which should always be used when rendering templates related
    #: to a single model. A practical example might be adding the same sidebar
    #: to all resources related to a specific model.
    base_template = 'base.html'

    #: The model. Required.
    model = None

    #: Overrides the queryset used for rendering. Override ``get_queryset``
    #: below if you have more advanced needs.
    queryset = None

    #: Part of the template name. Is set in most view classes to a sane value
    #: such as ``_list``, ``_detail``, ``_form`` or something similar.
    template_name_suffix = None

    def url(self, item, *args, **kwargs):
        """
        Helper for reversing URLs related to the resource model. Works the
        same way as ``towel.modelview.ModelViewURLs`` (and is most useful
        if used together).

        Usage examples::

            self.url('list')

            self.url('edit', pk=self.object.pk)
            # equals self.object.urls.url('edit') if using ModelViewURLs
        """
        fail_silently = kwargs.pop('fail_silently', False)

        try:
            if getattr(self, 'object', None):
                return self.object.urls.url(item, *args, **kwargs)
            return self.model().urls.url(item, *args, **kwargs)
        except NoReverseMatch:
            if not fail_silently:
                raise
            return None

    def get_title(self):
        """
        Returns a sane value for the ``title`` template context variable.
        """
        return None

    def get_context_data(self, **kwargs):
        """
        Fills the standard context with default variables useful for all
        model resource views:

        - ``base_template``: Described above.
        - ``verbose_name`` and ``verbose_name_plural``: Current model.
        - ``view``: The view instance.
        - ``add_url`` and ``list_url``: The mose important URLs for the model.
        - ``title``: Described above.
        """
        opts = self.model._meta
        context = {
            'base_template': self.base_template,
            'verbose_name': opts.verbose_name,
            'verbose_name_plural': opts.verbose_name_plural,
            'view': self,

            'add_url': self.url('add', fail_silently=True),
            'list_url': self.url('list', fail_silently=True),
        }
        title = self.get_title()
        if title:
            context['title'] = title
        context.update(kwargs)
        return context

    def get_template_names(self):
        """
        Returns a list of template names related to the current model and view:

        - ``self.template_name`` if it's set.
        - ``<app_label>/<model_name><template_name_suffix>.html
        - ``resources/object<template_name_suffix>.html
        """
        names = [
            '{0}/{1}{2}.html'.format(
                *(app_model_label(self.model) + (self.template_name_suffix,))),
            'resources/object{0}.html'.format(self.template_name_suffix),
        ]
        if self.template_name:
            names.insert(0, self.template_name)
        return names

    def get_queryset(self):
        """
        Returns the queryset used everywhere.

        Defaults to ``self.model._default_manager.all()``.
        """
        if self.queryset is not None:
            return self.queryset._clone()
        elif self.model is not None:
            return self.model._default_manager.all()
        else:
            raise ImproperlyConfigured("'%s' must define 'queryset' or 'model'"
                                       % self.__class__.__name__)

    def get_object(self):
        """
        Returns a single object for detail views or raises ``Http404``.

        The default implementation passes all keyword arguments extracted from
        the URL into ``get_object_or_404``.
        """
        return get_object_or_404(self.get_queryset(), **self.kwargs)

    def allow_add(self, silent=True):
        """
        Whether adding objects should be allowed. Defaults to ``True``.

        If ``silent=False`` you can optionally add a message in your own
        implementation.
        """
        return True

    def allow_edit(self, object=None, silent=True):
        """
        Whether editing objects should be allowed. Defaults to ``True``.

        Should determine whether editing objects is allowed under any
        circumstances if ``object=None``.
        """
        return True

    def allow_delete(self, object=None, silent=True):
        """
        Whether deleting objects should be allowed. Defaults to ``False``.

        Should determine whether editing objects is allowed under any
        circumstances if ``object=None``.

        Adds a message that deletion is not allowed when ``silent=False``.
        """
        if not silent:
            opts = self.model._meta
            if object is None:
                messages.error(self.request, _(
                    'You are not allowed to'
                    ' delete %(verbose_name_plural)s.'
                ) % opts.__dict__)
            else:
                messages.error(self.request, _(
                    'You are not allowed to'
                    ' delete this %(verbose_name)s.'
                ) % opts.__dict__)
        return False

    def allow_delete_if_only(self, object, related=(), silent=True):
        """
        This helper is most useful when used inside ``allow_delete``. It can
        be used to easily determine whether there are related instances which
        would be deleted as well.

        Returns ``True`` if the classes only belong to the model itself and
        to the classes mentioned in ``related``.
        """
        classes = set(related_classes(object)).difference(
            (self.model,), related)
        if not classes:
            return True
        if not silent:
            messages.error(
                self.request,
                _('Deletion not allowed because of related objects: %s') % (
                    ', '.join(
                        force_text(cls._meta.verbose_name_plural)
                        for cls in classes
                    ),
                )
            )
        return False


class ListView(ModelResourceView):
    """
    View used for listing objects. Has support for pagination, search forms
    and batch actions similar to the actions built into Django's admin
    interface.
    """

    #: Objects per page. Defaults to ``None`` which means no pagination.
    paginate_by = None

    #: Search form class.
    search_form = None

    #: ``object_list.html`` it is.
    template_name_suffix = '_list'

    def get_paginate_by(self, queryset):
        """
        Returns the value of ``self.paginate_by``.
        """
        # if self.paginate_all_allowed and self.request.GET.get('all'):
        #     return None
        return self.paginate_by

    def get_context_data(self, object_list=None, **kwargs):
        """
        Adds ``object_list`` to the context, and ``page`` and ``paginator``
        as well if paginating.
        """
        context = super(ListView, self).get_context_data(
            object_list=object_list, **kwargs)

        if object_list is not None:
            paginate_by = self.get_paginate_by(object_list)
            if paginate_by:
                paginator = Paginator(object_list, paginate_by)

                try:
                    page = int(self.request.GET.get('page'))
                except (TypeError, ValueError):
                    page = 1
                try:
                    page = paginator.page(page)
                except (EmptyPage, InvalidPage):
                    page = paginator.page(paginator.num_pages)

                context.update({
                    'object_list': page.object_list,
                    'page': page,
                    'paginator': paginator,
                })

        return context

    def get(self, request, *args, **kwargs):
        """
        Handles the search form and batch action handling.
        """
        self.object_list = self.get_queryset()
        context = {}

        if self.search_form:
            form = self.search_form(self.request.GET, request=self.request)
            if not form.is_valid():
                messages.error(
                    self.request, _('The search query was invalid.'))
                return HttpResponseRedirect('?clear=1')
            self.object_list = safe_queryset_and(
                self.object_list,
                form.queryset(self.model),
            )
            context['search_form'] = form

        context.update(self.get_context_data(object_list=self.object_list))

        actions = self.get_batch_actions()
        if actions:
            form = BatchForm(self.request, self.object_list)
            form.actions = actions
            form.fields['action'] = forms.ChoiceField(
                label=_('Action'),
                choices=[('', '---------')] + [row[:2] for row in actions],
                widget=forms.HiddenInput,
            )
            context['batch_form'] = form

            if form.should_process():
                action = form.cleaned_data.get('action')
                name, title, fn = [a for a in actions if action == a[0]][0]
                result = fn(form.batch_queryset)
                if isinstance(result, HttpResponse):
                    return result
                elif hasattr(result, '__iter__'):
                    messages.success(
                        self.request,
                        _(
                            '<p>Processed the following items:</p>'
                            ' <ul><li>%s</li></ul>'
                        ) % (
                            '</li><li>'.join(
                                force_text(item) for item in result
                            )
                        )
                    )
                elif result is not None:
                    # Not None, but cannot make sense of it either.
                    raise TypeError('Return value %r of %s invalid.' % (
                        result, fn.__name__))

                return redirect(self.url('list'))

        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        """
        Calls ``self.get`` because of the batch action handling.
        """
        return self.get(request, *args, **kwargs)

    def get_batch_actions(self):
        """
        Returns a list of batch action tuples ``(key, name, handler_fn)``

        * ``key``: Something nice, such as ``delete_selected``.
        * ``name``: Will be shown in the dropdown.
        * ``handler_fn``: Callable. Receives the request and the queryset.
        """
        return [
            ('delete_selected', _('Delete selected'), self.delete_selected),
        ]

    def batch_action_hidden_fields(self, queryset, additional=[]):
        """
        Returns a blob of HTML suitable for jumping back into the batch
        action handler. Most useful for batch action handlers needing to
        present a confirmation and/or form page to the user.

        See ``delete_selected`` below for the usage.
        """
        post_values = [('batchform', 1)] + additional + [
            ('batch_%s' % item.pk, '1') for item in queryset]

        return '\n'.join(
            '<input type="hidden" name="%s" value="%s">' % item
            for item in post_values)

    def delete_selected(self, queryset):
        """
        Action which deletes all selected items provided:

        - Their deletion is allowed.
        - Confirmation is given on a confirmation page.
        """
        allowed = [self.allow_delete(item) for item in queryset]
        queryset = [item for item, perm in zip(queryset, allowed) if perm]

        if not queryset:
            messages.error(self.request, _(
                'You are not allowed to delete any'
                ' object in the selection.'))
            return

        elif not all(allowed):
            messages.warning(self.request, _(
                'Deletion of some objects not allowed. Those have been'
                ' excluded from the selection already.'))

        if 'confirm' in self.request.POST:
            messages.success(self.request, _('Deletion successful.'))
            # Call all delete() methods individually
            [item.delete() for item in queryset]
            return

        context = super(ListView, self).get_context_data(
            title=_('Delete selected'),
            action_queryset=queryset,
            action_hidden_fields=self.batch_action_hidden_fields(queryset, [
                ('batch-action', 'delete_selected'),
                ('confirm', 1),
            ]),
        )
        self.template_name_suffix = '_action'
        return self.render_to_response(context)


class DetailView(ModelResourceView):
    """
    Detail view. Nuff said.
    """
    template_name_suffix = '_detail'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    @classmethod
    def render_regions(cls, view, **kwargs):
        """
        This is mostly helpful when using ``{% region %}`` template tags. It
        returns all regions when rendering the detail page of the passed
        view. Those regions still have to be filtered using ``changed_regions``
        if you do not want to exchange all snippets.

        When editing data which is used to render a detail page of the same
        or of a different, related model instance, rendering the detail page
        and extracting (potentially) changed parts is necessary for
        live-updating the affected HTML snippets in the frontend.

        This class method achieves exactly that.

        Usage examples::

            # When editing the same model as is on display
            regions = DetailView.render_regions(self)

            # When using towel.resources.inlines
            regions = DetailView.render_regions(self,
                model=self.get_parent_class(),
                object=self.parent,
                )
        """
        self = cls()
        self.request = view.request
        self.model = view.model
        self.object = view.object  # This is, of course, not always correct.
        for key, value in kwargs.items():
            setattr(self, key, value)

        regions = {}
        context = self.get_context_data(object=self.object, regions=regions)
        self.render_to_response(context).render()
        return regions


class FormView(ModelResourceView):
    """
    Base class for all views handling forms (creations and updates).
    """

    #: Base form class used for editing objects. The default implementation
    #: of ``get_form_class`` below always uses ``modelform_factory`` with
    #: a custom ``formfield_callback``.
    form_class = forms.ModelForm

    #: The object being edited (or ``None`` if creating a new object).
    object = None

    #: ``object_form.html`` should be enough for everyone.
    template_name_suffix = '_form'

    def get_title(self):
        """
        Returns titles suitable for adding or editing objects depending on
        whether ``self.object`` is set or not.
        """
        if self.object and self.object.pk:
            return capfirst(_('Edit %s') % self.object)
        return capfirst(_('Add %s') % self.model._meta.verbose_name)

    def get_form_kwargs(self, **kwargs):
        """
        Returns a dictionary suitable for initializing a model form instance
        when using the dictionary as keyword arguments.

        All passed keyword arguments are added to the dictionary, and may
        be used to override any of ``data``, ``files`` and ``instance``.
        """
        kw = {'instance': self.object}
        if self.request.method in ('POST', 'PUT'):
            kw.update({
                'data': self.request.POST,
                'files': self.request.FILES,
            })
        kw.update(kwargs)
        return kw

    def get_form_class(self):
        """
        Returns the form class used in the view.
        """
        return modelform_factory(
            self.model,
            form=self.form_class,
            fields='__all__',
            formfield_callback=towel_formfield_callback)

    def get_form(self):
        """
        Returns the form instance used in the view.
        """
        return self.get_form_class()(**self.get_form_kwargs())

    def form_valid(self, form):
        """
        Processes the form if validation succeeded.

        The default implementation saves the form first and redirects to
        the detail URL of the returned instance.
        """
        self.object = form.save()
        messages.success(
            self.request,
            _('The %(verbose_name)s has been successfully saved.') %
            self.object._meta.__dict__,
        )
        return redirect(self.object)

    def form_invalid(self, form):
        """
        Processes the form if validation failed.

        The default implementation renders the form again.
        """
        context = self.get_context_data(form=form, object=self.object)
        return self.render_to_response(context)


class AddView(FormView):
    """
    View class handling the creation of new items.

    Checks whether adding objects is allowed first and redirects to the
    list URL for the current model if not.
    """
    def get(self, request, *args, **kwargs):
        if not self.allow_add(silent=False):
            return redirect(self.url('list'))
        form = self.get_form()
        return self.render_to_response(self.get_context_data(form=form))

    def post(self, request, *args, **kwargs):
        if not self.allow_add(silent=False):
            return redirect(self.url('list'))
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)


class EditView(FormView):
    """
    View class handling the editing of existing items.

    Fetches the instance from the database first and checks whether editing
    it is allowed next. The permission check is done second because the result
    might depend on the exact object.

    The return value of not found versus permission denied exposes some
    additional information right now. This will not necessarily stay like that
    in the future, do not rely on it.
    """
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not self.allow_edit(self.object, silent=False):
            return redirect(self.object)
        form = self.get_form()
        context = self.get_context_data(form=form, object=self.object)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not self.allow_edit(self.object, silent=False):
            return redirect(self.object)
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)


class LiveUpdateAfterEditMixin(object):
    """
    Only uses the editlive mechanism for updating. The edit step happens
    inside a standard modal.
    """
    def form_valid(self, form):
        self.object = form.save()

        regions = DetailView.render_regions(self)
        data = {'!form-errors': {}}
        data.update(changed_regions(regions, form.changed_data))
        return HttpResponse(json.dumps(data), content_type='application/json')


class LiveFormView(LiveUpdateAfterEditMixin, FormView):
    """
    View most useful if the detail page contains editlive input fields. This
    is the POST-only resource for updates.

    Only supports updating fields on the model itself, and no many to many
    fields either.
    """
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not self.allow_edit(self.object, silent=True):
            raise PermissionDenied

        form_class = self.get_form_class()
        data = model_to_dict(
            self.object,
            fields=form_class._meta.fields,
            exclude=form_class._meta.exclude)

        for key, value in request.POST.items():
            data[key] = value

        form = form_class(**self.get_form_kwargs(data=data))

        if form.is_valid():
            return self.form_valid(form)

        return HttpResponse(
            json.dumps({'!form-errors': dict(form.errors)}),
            content_type='application/json')


class PickerView(ModelResourceView):
    """
    View handling a picker opened in a modal layer. Requires the editlive
    Javascript code to be loaded for searches to work.
    """
    template_name_suffix = '_picker'

    def get_title(self):
        return capfirst(_('Select a %s') % self.model._meta.verbose_name)

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        regions = None
        query = request.GET.get('query')

        if query is not None:
            self.object_list = safe_queryset_and(
                self.object_list,
                self.model.objects._search(query))
            regions = {}

        context = self.get_context_data(
            object_list=self.object_list,
            regions=regions)
        response = self.render_to_response(context)

        if query is not None:
            response.render()
            data = changed_regions(regions, ['object_list'])
            data['!keep'] = True  # Keep modal open
            return HttpResponse(
                json.dumps(data),
                content_type='application/json')

        return response


class DeleteView(ModelResourceView):
    """
    View class handling the deletion of items.

    Fetches the instance from the database first and checks whether deletion
    it is allowed next. The permission check is done second because the result
    might depend on the exact object.

    The return value of not found versus permission denied exposes some
    additional information right now. This will not necessarily stay like that
    in the future, do not rely on it.

    This view uses a form for the confirmation. The default form is empty and
    validates for all POST requests. You can optionally specify your own form
    if additional confirmation is required.
    """
    #: ``object_delete_confirmation.html``.
    template_name_suffix = '_delete_confirmation'

    #: The form class used for deletions.
    deletion_form_class = forms.Form

    def get_title(self):
        return capfirst(_('Delete %s') % self.object)

    def get_deletion_form(self):
        """
        Returns the form instance. Customize this method if you need custom
        form initialization; ``get_form_class`` and ``get_form_kwargs`` are
        not available for deletions for simplicity.
        """
        if self.request.method == 'POST':
            return self.deletion_form_class(self.request.POST)
        return self.deletion_form_class()

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not self.allow_delete(self.object, silent=False):
            return redirect(self.object)
        form = self.get_deletion_form()
        context = self.get_context_data(object=self.object, form=form)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not self.allow_delete(self.object, silent=False):
            return redirect(self.object)
        form = self.get_deletion_form()
        if form.is_valid():
            return self.deletion_form_valid(form)
        return self.deletion_form_invalid(form)

    def deletion_form_valid(self, form):
        """
        On successful form validation, the object is deleted and the user is
        redirected to the list view of the model.
        """
        self.object.delete()
        messages.success(
            self.request,
            _('The %(verbose_name)s has been successfully deleted.') %
            self.object._meta.__dict__,
        )
        return redirect(self.url('list'))

    def deletion_form_invalid(self, form):
        context = self.get_context_data(object=self.object, form=form)
        return self.render_to_response(context)
