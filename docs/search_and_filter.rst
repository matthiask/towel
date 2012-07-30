.. _search:

=================
Search and Filter
=================

Towel does not distinguish between a search and a filter query.
There are different layers of filtering applied during a request and depending
on your need you have to hook in your filter at the right place.


.. _modelview-object-list-searchable:

Making lists searchable using the search form
=============================================

Pagination is not enough for many use cases, we need more! Luckily, Towel
has a pre-made solution for searching object lists too.

:py:class:`towel.forms.SearchForm` can be used together with
:py:class:`towel.managers.SearchManager` to build a low-cost implementation of
full text search and filtering by model attributes.

The method used to implement full text search is a bit stupid and cannot
replace mature full text search solutions such as Apache Solr. It might just
solve 80% of the problems with 20% of the effort though.

Code talks. First, we extend our models definition with a
:py:class:`~django.db.models.Manager` subclass with a simple search
implementation::

    from django.db import models
    from towel.managers import SearchManager

    class BookManager(SearchManager):
        search_fields = ('title', 'topic', 'authors__name',
            'publisher__name', 'publisher__address')

    class Book(models.Model):
        # [...]

        objects = BookManager()

:py:class:`~towel.managers.SearchManager` supports queries with multiple clauses;
terms may be grouped using apostrophes, plus and minus signs may be optionally
prepended to the terms to determine whether the given term should be included
or not. Example::

    +Django "Shop software" -Satchmo

Please note that you can search fields from other models too. You should
be careful when traversing many-to-many or reverse foreign key relations
however, because you will get duplicated results if you do not call
:py:meth:`~django.db.models.query.QuerySet.distinct` on the resulting queryset.

The method :py:meth:`~towel.managers.SearchManager._search` does the heavy
lifting when constructing a queryset. You should not need to override this
method. If you want to customize the results further, f.e. apply a site-wide
limit for the objects a certain logged in user may see, you should override
:py:meth:`~towel.managers.SearchManager.search`.

Next, we have to create a :class:`~towel.forms.SearchForm` subclass::

    from django import forms
    from towel import forms as towel_forms
    from myapp.models import Author, Book, Publisher

    class BookSearchForm(towel_forms.SearchForm):
        publisher = forms.ModelChoiceField(Publisher.objects.all(), required=False)
        authors = forms.ModelMultipleChoiceField(Author.objects.all(), required=False)
        published_on__lte = forms.DateField(required=False)
        published_on__gte = forms.DateField(required=False)

        formfield_callback = towel_forms.towel_formfield_callback


You have to add ``required=False`` to every field if you do not want validation
errors on the first visit to the form (which would not make a lot of sense, but
isn't actively harmful).

As long as you only use search form fields whose names correspond to the keywords
used in Django's ``.filter()`` calls or ``Q()`` objects you do not have to do
anything else.

The ``formfield_callback`` simply substitutes a few fields with whitespace-stripping
equivalents, and adds CSS classes to ``DateInput`` and ``DateTimeInput`` so that
they can be easily augmented by javascript code.

.. warning::

    If you want to be able to filter by multiple items, i.e. publishers 1 and 2,
    you have to define the ``publisher`` field in the ``SearchForm`` as
    :class:`~django.forms.ModelMultipleChoiceField`. Even if the model itself only
    has a simple ForeignKey Field. Otherwise only the last item in the URL is used
    for filtering.

To activate this search form, all you have to do is add an additional parameter
when you instantiate the ModelView subclass::

    from myapp.forms import BookSearchForm
    from myapp.models import Book
    from towel.modelview import ModelView

    urlpatterns = patterns('',
        url(r'^books/', include(ModelView(Book,
            search_form=BookSearchForm,
            paginate_by=20,
            ).urls)),
    )


.. warning::

    To distinguish between a search request and an ordinary form submission,
    towel requires that the POST parameter ``s`` exist
    if the form is sent via POST.
    The field is included by default, but don't forget to add it to your template
    if you are using a custom form render method.


You can now filter the list by providing the search keys as GET parameters::

    localhost:8000/books/?author=2
    localhost:8000/books/?publisher=4&o=authors
    localhost:8000/books/?authors=4&authors=5&authors=6


Advanced SearchForm features
----------------------------

The :class:`~towel.forms.SearchForm` has a ``post_init`` method,
which receives the request and is useful if you have to further modify
the queryset i.e. depending on the current user::

    def post_init(self, request):
        self.access = getattr(request.user, 'access', None)
        self.fields['publisher'] = forms.ModelChoiceField(
            Publisher.objects.for_access(self.access),
            required=False
        )


The ordering is also defined in the :class:`~towel.forms.SearchForm`.
You have to specify a dict called ``orderings`` which has the ordering key
as first parameter. The second parameter can be a field name, an iterable of
field names or a callable. The ordering keys are what is used in the URL::

    class AddressSearchForm(SearchForm):
        orderings = {
            '': ('last_name', 'first_name'), # Default
            'dob': 'dob', # Sort by date of birth
            'random': lambda queryset: queryset.order_by('?'),
            }


Persistent queries
==================

When you pass the parameter ``s``, the search is stored in the session for
that path. If the user returns to the object list, the filtering is applied again.
To reset the filters, you have to pass ``?n`` or ``?query=`` (an empty query).


Quick Rules
===========

Another option for filtering are :doc:`Quick rules <autogen/quick>`.
This allows for field-independent filtering like ``is:cool``.
Quick rules are mapped to filter attributes using regular expressions.
They go into the search form and are parsed automatically::

    class BookSearchForm(towel_forms.SearchForm):
        quick_rules = [
            (re.compile(r'has:publisher'), quick.static(publisher__isnull=False)),
            (re.compile(r'is:published'), quick.static(published_on__lt=timezone.now)),
        ]
