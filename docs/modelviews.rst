.. _modelviews:

=========
ModelView
=========

.. currentmodule:: towel.modelview


We'll start with simple object list and object detail pages, explaining many
provided tools along the way. Next, this guide covers the CRUD part of Towel,
talk about batch processing a bit and end up with explaining a few components
in more detail.

.. warning::

    Please note that Towel's ModelView could be considered similar to Django's
    own generic views. However, they do not have the same purpose and software
    design: Django's generic views use one class per view, and every instance
    only processes one request. Towel's ModelView is more similar to Django's
    admin site in that one instance is responsible for many URLs and handles
    many requests.  You have to take care not to modify ModelView itself during
    request processing, because this will not be thread-safe.


.. _modelview-models:

Preparing your models, views and URLconfs for ModelView
=======================================================

ModelView has a strong way of how Django-based web applications should be
written. The rigid structure is necessary to build a well-integrated toolset
which will bring you a long way towards successful completion of your project.
If you do not like the design decisions made, ModelView offers hooks to
customize the behavior, but that's not covered in this guide.

For this guide, we assume the following model structure and relationships::

    from django.db import models

    class Publisher(models.Model):
        name = models.CharField(max_length=100)
        address = models.TextField()

    class Author(models.Model):
        name = models.CharField(max_length=100)
        date_of_birth = models.DateField(blank=True, null=True)

    class Book(models.Model):
        title = models.CharField(max_length=100)
        topic = models.CharField(max_length=100)
        authors = models.ManyToManyField(Author)
        published_on = models.DateField()
        publisher = models.ForeignKey(Publisher)


ModelView works with an URL structure similar to the following:

* ``/books/``
* ``/books/add/``
* ``/books/<pk>/``
* ``/books/<pk>/edit/``
* ``/books/<pk>/delete/``

The regular expression used to match the detail page (here <pk>) can be
customized. If you'd rather match on the slug, on a combination of
several fields (separated by dashes or slashes, whatever you want) or on
something else, you can do this by modifying
:py:attr:`~ModelView.urlconf_detail_re`. You only have to make sure that
:py:func:`~ModelView.get_object` will know what to do with the extracted
parameters.

If you want to use the primary key-based URL configuration, you do not
need to add a :py:func:`~django.db.models.Model.get_absolute_url` method to
your model, because :py:class:`ModelView` will add one itself. It isn't
considered good practice to put primary keys on the web for everyone to see
but it might be okay for your use case.


.. _modelview-modelview:

The main ``ModelView`` class
============================

.. class:: ModelView(model, [...])

    The first and only required argument when instantiating a model view is
    the Django model. Additional keyword arguments may be used to override
    attribute values of the model view class. It is not allowed to pass
    keyword arguments which do not exist as attributes on the class already.

    .. attribute:: urlconf_detail_re

        The regular expression used for detail pages. Defaults to a regular
        expression which only accepts a numeric primary key.

    .. attribute:: paginate_by

        Objects per page for list views. Defaults to ``None`` which means
        that all objects are shown on one page (usually a bad idea).

    .. attribute:: pagination_all_allowed

        Pagination can be deactivated by passing ``?all=1`` in the URL.
        If you expect having lots of objects in the table showing all on
        one page can lead to a very slow and big page being shown. Set
        this attribute to ``False`` to disallow this behavior.

    .. attribute:: paginator_class

        Paginator class which should have the same interface as
        :py:class:`django.core.paginator.Paginator`. Defaults to
        :py:class:`towel.paginator.Paginator` which is almost the same as
        Django's, but offers additional methods for outputting Digg-style
        pagination links.

    .. attribute:: template_object_name

        The name used for the instance in detail and edit views. Defaults
        to ``object``.

    .. attribute:: template_object_list_name

        The name used for instances in list views. Defaults to
        ``object_list``.

    .. attribute:: base_template

        The template which all standard modelview templates extend. Defaults
        to ``base.html``.

    .. attribute:: form_class

        The form class used to create and update models. The method
        :py:func:`~ModelView.get_form` returns this value instead of invoking
        :py:func:`~django.forms.models.modelform_factory` if it is set.
        Defaults to ``None``.

    .. attribute:: search_form

        The search form class to use in list views. Should be a subclass of
        :py:class:`towel.forms.SearchForm`. Defaults to ``None``, which
        deactivates search form handling.

    .. attribute:: search_form_everywhere

        Whether a search form instance should be added to all views, not only
        to list views. Useful if the search form is shown on detail pages
        as well.

    .. attribute:: batch_form

        The batch form class used for batch editing in list views. Should be
        a subclass of :py:class:`towel.forms.BatchForm`. Defaults to ``None``.

    .. attribute:: default_messages

        A set of default messages for various success and error conditions.
        You should not modify this dictionary, but instead override messages
        by adding them to :py:attr:`~ModelView.custom_messages` below. The
        current set of messages is:

        - ``object_created``
        - ``adding_denied``
        - ``object_updated``
        - ``editing_denied``
        - ``object_deleted``
        - ``deletion_denied``
        - ``deletion_denied_related``

        Note that by modifying this dictionary you are modifying it for all
        model view instances!

    .. attribute:: custom_messages

        A set of custom messages for custom actions or for overriding messages
        from  :py:attr:`~ModelView.custom_messages`.

        Note that by modifying this dictionary you are modifying it for all
        model view instances! If you want to override a few messages only for
        a particular model view instance, you have to set this attribute to
        a new dictionary instance, not update the existing dictionary.

    .. method:: view_decorator(self, func)
    .. method:: crud_view_decorator(self, func)

        The default implementation of :py:func:`~ModelView.get_urls` uses
        those two methods to decorate all views, the former for list and detail
        views, the latter for add, edit and delete views.


.. currentmodule:: towel.modelview.ModelView
.. _modelview-models-querysets:

Models and querysets
--------------------

.. method:: get_query_set(self, request, \*args, \*\*kwargs)

    This method should return a queryset with all objects this modelview
    is allowed to see. If a certain user should only ever see a subset of
    all objects, add the permission checking here. Example::

        class UserModelView(ModelView):
            def get_query_set(self, request, *args, **kwargs):
                return self.model.objects.filter(created_by=request.user)

.. unconfuse vim's syntax highlighting * **

    The default implementation returns all objects which can be seen by
    the first manager defined on the Django model.

.. method:: get_object(self, request, \*args, \*\*kwargs)

    Returns a single object for the query parameters passed as ``args`` and
    ``kwargs`` or raises a :py:exc:`~django.core.exceptions.ObjectDoesNotExist`
    exception. The default implementation passes all args and kwargs to
    a :py:func:`~django.db.models.QuerySet.get` call, which means that all
    parameters extracted by the :py:attr:`urlconf_detail_re` regular
    expression should uniquely identify the object in the queryset returned
    by :py:func:`get_query_set` above.

.. method:: get_object_or_404(self, request, \*args, \*\*kwargs)

    Wraps :py:func:`get_object`, but raises a :py:class:`~django.http.Http404`
    instead of a :py:exc:`~django.core.exceptions.ObjectDoesNotExist`.


.. _modelview-object-list:

Object lists
------------

Towel`s object lists are handled by :py:func:`list_view`. By default,
all objects are shown on one page but this can be modified through
:py:attr:`paginate_by`. The following code puts a paginated list of
books at ``/books/``::

    from myapp.models import Book
    from towel.modelview import ModelView

    class BookModelView(ModelView):
        paginate_by = 20

    book_views = BookModelView(Book)

    urlpatterns = patterns('',
        url(r'^books/', include(book_views.urls)),
    )


This can even be written shorter if you do not want to override any ModelView
methods::

    from myapp.models import Book
    from towel.modelview import ModelView

    urlpatterns = patterns('',
        url(r'^books/', include(ModelView(Book, paginate_by=20).urls)),
    )


The model instances are passed as ``object_list`` into the template by default.
This can be customized by setting :py:attr:`template_object_list_name`
to a different value.

The :py:func:`list_view` method does not contain much code, and simply defers to
other methods who do most of the grunt-work. Those methods are shortly explained
here.

.. method:: list_view(self, request)

   Main entry point for object lists, calls all other methods.


.. method:: handle_search_form(self, request, ctx, queryset=None)
.. method:: handle_batch_form(self, request, ctx, queryset)

   These methods are discussed later, under :ref:`modelview-object-list-searchable` and
   :ref:`modelview-batch-processing`.


.. method:: paginate_object_list(self, request, queryset, paginate_by=10)

   If ``paginate_by``is given paginates the object list using the ``page`` GET
   parameter. Pagination can be switched off by passing ``all=1`` in the GET
   request. If you have lots of objects and want to disable the ``all=1``
   parameter, set ``pagination_all_allowed`` to ``False``.


.. method:: render_list(self, request, context)

   The rendering of object lists is done inside ``render_list``. This method
   calls ``get_template`` to assemble a list of templates to try, and
   ``get_context`` to build the context for rendering the final template. The
   templates tried are as follows:

   * ``<app_label>/<model_name>_list.html`` (in our case, ``myapp/book_list.html``)
   * ``modelview/object_list.html``

   The additional variables passed into the context are documented in
   :ref:`modelview-standard-context`.


.. _modelview-object-list-searchable:

List Searchable
===============

Please refer to the :doc:`search_and_filter` page for information about
filtering lists.


.. _modelview-object-detail:

Object detail pages
===================

Object detail pages are handled by :py:func:`detail_view`. All parameters
captured in the :py:attr:`urlconf_detail_re` regex are passed on to
:py:func:`get_object_or_404`, which passes them to :py:func:`get_object`.
:py:func:`get_object` first calls :py:func:`get_query_set`, and tries finding
a model thereafter.

The rendering is handled by :py:func:`render_detail`; the templates tried are

* ``<app_label>/<model_name>_detail.html`` (in our case, ``myapp/book_detail.html``)
* ``modelview/object_detail.html``

The model instance is passed as ``object`` into the template by default. This
can be customized by setting ``template_object_name`` to a different value.


.. _modelview-adding-updating:

Adding and updating objects
===========================

Towel offers several facilities to make it easier to build and process complex
forms composed of forms and formsets. The code paths for adding and updating
objects are shared for a big part.

``add_view`` and ``edit_view`` are called first. They defer most of their work
to helper methods.

.. method:: add_view(self, request)

   ``add_view`` does not accept any arguments.


.. method:: edit_view(self, request, \*args, \*\*kwargs)

   ``args`` and ``kwargs`` are passed as they are directly into
   :py:func:`get_object`.


.. method:: process_form(self, request, intance=None, change=None)

   These are the common bits of :py:meth:`add_view` and :py:meth:`edit_view`.


.. method:: get_form(self, request, instance=None, change=None, \*\*kwargs)

   Return a Django form class. The default implementation returns the result
   of calling :py:func:`~django.forms.models.modelform_factory`. Keyword
   arguments are forwarded to the factory invocation.


.. method:: get_form_instance(self, request, form_class, instance=None, change=None, \*\*kwargs)

   Instantiate the form, for the given instance in the editing case.

   The arguments passed to the form class when instantiating are determined by
   ``extend_args_if_post`` and ``**kwargs``.


.. method:: extend_args_if_post(self, request, args)

   Inserts ``request.POST`` and ``request.FILES`` at the beginning of ``args``
   if ``request.method`` is ``POST``.


.. method:: get_formset_instances(self, request, instance=None, change=None, \*\*kwargs)

   Returns an empty ``dict`` by default. Construct your formsets if you want
   any in this method::

       BookFormSet = inlineformset_factory(Publisher, Book)

       class PublisherModelView(ModelView):
           def get_formset_instances(self, request, instance=None, change=None, **kwargs):
               args = self.extend_args_if_post(request, [])
               kwargs.setdefault('instance', instance)

               return {
                   'books': BookFormSet(prefix='books', *args, **kwargs),
                   }

.. method:: save_form(self, request, form, change)

   Return an unsaved instance when editing an object. ``change`` is ``True``
   if editing an object.


.. method:: save_model(self, request, instance, form, change)

   Save the instance to the database. ``change`` is ``True`` if editing
   an object.


.. method:: save_formsets(self, request, form, formsets, change)

   Iterates through the ``formsets`` ``dict``, calling ``save_formset`` on
   each.


.. method:: save_formset(self, request, form, formset, change)

   Actually saves the formset instances.


.. method:: post_save(self, request, form, formsets, change)

   Hook for adding custom processing after forms, formsets and m2m relations
   have been saved. Does nothing by default.


.. method:: render_form(self, request, context, change)

   Offloads work to ``get_template``, ``get_context`` and ``render_to_response``.
   The templates tried when rendering are:

   * ``<app_label>/<model_name>_form.html``
   * ``modelview/object_form.html``


.. method:: response_add
.. method:: response_edit

   They add a message using the ``django.contrib.messages`` framework and redirect
   the user to the appropriate place, being the detail page of the edited object
   or the editing form if ``_continue`` is contained in the POST request.



.. _modelview-deletion:

Object deletion
===============

Object deletion through ModelView is forbidden by default as a safety measure.
However, it is very easy to allow deletion globally::

    class AuthorModelView(ModelView):
        def deletion_allowed(self, request, instance):
            return True


If you wanted to allow deletion only for the creator, you could use something
like this::

    class AuthorModelView(ModelView):
        def deletion_allowed(self, request, instance):
            # Our author model does not have a created_by field, therefore this
            # does not work.
            return request.user == instance.created_by


Often, you want to allow deletion, but only if no related objects are affected
by the deletion. ModelView offers a helper to do that::

    class PublisherModelView(ModelView):
        def deletion_allowed(self, request, instance):
            return self.deletion_allowed_if_only(request, instance, [Publisher])


If there are any books in our system published by the given publisher instance,
the deletion would not be allowed. If there are no related objects for this
instance, the user is asked whether he really wants to delete the object. If
he confirms, the instance is or the instances are deleted for good, depending
on whether there are related objects or not.


Deletion of inline formset instances
------------------------------------

Django's inline formsets are very convenient to edit a set of related objects
on one page. When deletion of inline objects is enabled, it's much too easy
to lose related data because of Django's cascaded deletion behavior. Towel
offers helpers to allow circumventing Django's inline formset deletion behavior.

.. note::

   The problem is that ``formset.save(commit=False)`` deletes objects marked
   for deletion right away even though ``commit=False`` might be interpreted
   as not touching the database yet.

The models edited through inline formsets have to be changed a bit::

    from django.db import models
    from towel import deletion

    class MyModel(deletion.Model):
        field = models.CharField(...) # whatever

``deletion.Model`` only consists of a customized ``Model.delete`` method
which does not delete the model under certain circumstances. See the
:ref:`autogen-deletion` API documentation if you need to know more.

Next, you have to override ``save_formsets``::

    class MyModelView(modelview.ModelView):
        def get_formset_instances(self, request, instance=None, change=None, **kwargs):
            args = self.extend_args_if_post(request, [])
            kwargs['instance'] = instance

            return {
                'mymodels': InlineFormSet(*args, **kwargs),
                }

        def save_formsets(self, request, form, formsets, change):
            # Only delete MyModel instances if there are no related objects
            # attached to them
            self.save_formset_deletion_allowed_if_only(
                request, form, formsets['mymodels'], change, [MyModel])


.. warning::

   ``save_formset_deletion_allowed_if_only`` calls ``save_formset`` do actually
   save the formset. If you need this customized behavior, you must not call
   ``save_formset_deletion_allowed_if_only`` in ``save_formset`` or you'll get
   infinite recursion.


.. _modelview-standard-context:

Standard context variables
==========================

The following variables are always added to the context:

* ``verbose_name``
* ``verbose_name_plural``
* ``list_url``
* ``add_url``
* ``base_template``
* ``search_form`` if :py:attr:`search_form_everywhere` is ``True``

:py:class:`~django.template.RequestContext` is used, therefore all configured
context processors are executed too.


.. _modelview-permissions:

Permissions
===========

:py:func:`get_urls` assumes that there are two groups of users with
potentially differing permissions: Those who are only allowed to view and those
who may add, change or update objects.

To restrict viewing to authenticated users and editing to managers, you could
do the following::

    from django.contrib.admin.views.decorators import staff_member_required
    from django.contrib.auth.decorators import login_required

    book_views = BookModelView(Book,
        search_form=BookSearchForm,
        paginate_by=20,
        view_decorator=login_required,
        crud_view_decorator=staff_member_required,
        )

If :py:func:`crud_view_decorator` is not provided, it defaults to
:py:func:`view_decorator`, which defaults to returning the function as-is.
This means that by default, you do not get any view decorators.

Additionally, ModelView offers the following hooks for customizing permissions:

.. method:: adding_allowed(self, request)
.. method:: editing_allowed(self, request, instance)

    Return ``True`` by default.

.. method:: deletion_allowed(self, request, instance)

   Was already discussed under :ref:`modelview-deletion`. Returns ``False``
   by default.


.. _modelview-batch-processing:

Batch processing
================

Suppose you want to change the publisher for a selection of books. You could
do this by editing each of them by hand, or by thinking earlier and doing this::


    from django import forms
    from django.contrib import messages
    from towel import forms as towel_forms
    from myapp.models import Book, Publisher

    class BookBatchForm(towel_forms.BatchForm):
        publisher = forms.ModelChoiceField(Publisher.objects.all(), required=False)

        formfield_callback = towel_forms.towel_formfield_callback

        def _context(self, batch_queryset):
            data = self.cleaned_data

            if data.get('publisher'):
                messages.success(request, 'Updated %s books.' % (
                    batch_queryset.update(publisher=data.get('publisher')),
                    ))

            return {
                'batch_items': batch_queryset,
                }


Activate the batch form like this::

    book_views = BookModelView(Book,
        batch_form=BookBatchForm,
        search_form=BookSearchForm,
        paginate_by=20,
        )


If you have to return a response from the batch form (f.e. because you want to
generate sales reports for a selection of books), you can return a response in
``_context`` using the special-cased key ``response``::

    def _context(self, batch_queryset):
        # [...]

        return {
            'response': HttpResponse(your_report,
                content_type='application/pdf'),
            }
