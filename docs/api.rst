.. _api:

Towel API
*********

.. currentmodule:: towel.api

:py:mod:`towel.api` is a set of classes which facilitate building a RESTful
API. In contrast to other, well known projects such as
`django-piston <https://bitbucket.org/jespern/django-piston/>`_ and
`tastypie <http://tastypieapi.org/>`_ it does not try to cover all HTTP
verbs out of the box, and does not come with as many configuration knobs
and classes for everything, and tries staying small and simple instead.

The API consists of the following classes and methods, which are explained
in more depth further down this page:

- :py:class:`API`:
  A collection of resources.
- :py:class:`Resource`:
  A single resource which exposes a Django model instance.
- :py:class:`Serializer`:
  The API response serializer, responsible for content type negotiation
  and creation of :py:class:`~django.http.HttpResponse` instances.
- :py:class:`RequestParser`:
  Understands requests in various formats (JSON, urlencoded, etc.) and
  handles the differences.
- :py:class:`APIException`:
  An exception which can be raised deep down in the API / resource machinery
  and will be converted into a nicely formatted response in the requested
  content format.
- :py:class:`Objects` and :py:class:`Page`:
  Containers for objects related to a particular resource and / or URI.
  They are returned by the method :py:meth:`Resource.objects`.
- :py:func:`api_reverse`:
  Helper for reversing URLs inside a particular API instance.
- :py:func:`serialize_model_instance`:
  The default Django model serializer.
- :py:func:`querystring`:
  Helper for constructing querystrings.


.. _api-api:

The ``API`` class
=================

.. class:: API(name, decorators=[csrf_exempt])

    This class acts as a collection of resources. The arguments are:

    - ``name``: The name of this API. If you don't know what to use here,
      simply use ``'v1'``.
    - ``decorators``: A list of decorators which should be applied to the
      root API view and to all resources (if you don't override it upon
      resource registration). The list of decorators is applied in reverse,
      which means that you should follow the same order as if you were using
      the ``@decorator`` notation. It's recommended to always use
      :py:func:`~django.views.decorators.csrf.csrf_exempt` here, otherwise
      API requests other than GET, HEAD, OPTIONS and TRACE (the HTTP verbs
      defined as safe by RFC2616) will have to include a valid CSRF
      middleware token.

    Example::

        api_v1 = API('v1')


    .. attribute:: name

        The name of this API.

    .. attribute:: decorators

        The decorators passed upon initialization.

    .. attribute:: resources

        A list of dictionaries holding resource configuration.

    .. attribute:: serializers

        A dictionary mapping models to serialization functions. If a model
        does not exist inside this dictionary, the default serialization
        function :py:func:`serialize_model_instance` is used.


    .. attribute:: urls

        This property returns a URL pattern instance suitable for including
        inside your main URLconf::

            from .views import api_v1

            urlpatterns = patterns('',
                url(r'^api/v1/', include(api_v1.urls)),
            )

    .. method:: register(self, model, view_class=None, canonical=True, decorators=None, prefix=None, view_init=None, serializer=None)

        Resources are normally not created by hand. This method should be
        used instead. The arguments are:

        - ``model``: The Django model used in this resource.
        - ``view_class``: The resource view class used, defaults to
          :py:class:`Resource`.
        - ``canonical``: Whether this resource is the canonical location of the
          model in this API. Allows registering the same model several times in
          the API (only one location should be the canonical location!)
        - ``decorators``: A list of decorators which should be applied to the
          view. Function decorators only, method decorators aren't supported.
          The list is applied in reverse, the order is therefore the same as
          with the ``@decorator`` notation. If unset, the set of decorators
          is determined from the API initialization. Pass an empty list if you
          want no decorators at all.
        - ``prefix``: The prefix for this model, defaults to the model name in
          lowercase. You should include a caret and a trailing slash if you
          specify this yourself (``prefix=r'^library/'``).
        - ``view_init``: Python dictionary which contains keyword arguments
          used during the instantiation of the ``view_class``.
        - ``serializer``: Function which takes a model instance, the API
          instance and additional keyword arguments (accept ``**kwargs``
          for forward compatibility) and returns the serialized representation
          as a Python dictionary.

    .. method:: serialize_instance(self, instance, \**kwargs)

        Returns a serialized version of the passed model instance.

        This method should always be used for serialization, because it knows
        about custom serializers specified when registering resources with this
        API.

    .. method:: root(self, request)

        Main API view, returns a list of all available resources


.. _api-resources:

Resources
=========

.. class:: Resource(self, \**kwargs)

    This is a :py:class:`~django.views.generic.base.View` subclass with
    additional goodies for exposing a Django model in a RESTful way. You
    should not instantiate this class yourself, but use
    :py:meth:`API.register` instead.

    .. attribute:: api

        The :py:class:`API` instance to which this resource is bound to.

    .. attribute:: model

        The model exposed by this resource.

    .. attribute:: queryset

        Prefiltered queryset for this resource or ``None`` if all objects
        accessible through the first defined manager on the model should be
        exposed (or if you do the limiting yourself in
        :py:meth:`Resource.get_query_set`)

    .. attribute:: limit_per_page

        Standard count of items in a single request. Defaults to 20. This
        can be overridden by sending a different value with the ``limit``
        querystring parameter.

    .. attribute:: max_limit_per_page

        Maximal count of items in a single request. ``limit`` query values
        higher than this are not allowed. Defaults to 1000.

    .. attribute:: http_method_names

        Allowed HTTP method names. The :py:class:`Resource` only comes with
        implementations for GET, HEAD and OPTIONS. You have to implement
        all other handlers yourself.


A typical request-response cycle
--------------------------------

.. method:: Resource.dispatch(self, request, \*args, \**kwargs)

    This method is the primary entry point for requests. It is similar
    to the base class implementation but has a few important differences:

    - It uses ``self.request``, ``self.args`` and ``self.kwargs`` in
      all places.
    - It calls :py:meth:`~Resource.unserialize_request` after assigning the
      aforementioned variables on ``self`` which may modify all aspects
      and all variables (f.e.  deserialize a JSON request and serialize
      it again to look like a standard POST request) and only then
      determines whether the request should be handled by this view at
      all.
    - The return value of the :py:meth:`~Resource.get`,
      :py:meth:`~Resource.post` etc. methods is passed to
      :py:meth:`~Resource.serialize_response` and only then returned to
      the client. The processing methods should return a dictionary which
      is then serialized into the requested format. If the format is
      unknown or unsupported, a 406 Not acceptable HTTP error is returned
      instead.
    - :py:exc:`APIException` and :py:class:`~django.http.Http404`
      exceptions are caught and transformed into appropriate responses
      according to the content type requested.


.. method:: Resource.unserialize_request(self)

    This method's intent is to standardize various aspects of the incoming
    request so that the following code does not have to care about the format
    of the incoming data. It might decode incoming JSON data and reformat
    it as a standard HTTP POST.

    Currently, this method does nothing, and because of that, content is only
    accepted in two forms:

    - urlencoded in the request body
    - multipart in the request body


.. method:: Resource.get(self, request, \*args, \**kwargs)
.. method:: Resource.head(self, request, \*args, \**kwargs)

    These methods return serialized lists, sets or details depending upon
    the request URI.

    All of the following are valid URIs for a fictional resource for books:

    - ``/api/v1/book/``: Returns 20 books.
    - ``/api/v1/book/?offset=20&limit=20``: Returns books 21-40.
    - ``/api/v1/book/42/``: Returns the book with the primary key of 42.
    - ``/api/v1/book/1;3;15/``: Returns a set of three books.

    The :py:meth:`~Resource.get` method offloads processing into three
    distinct methods depending upon the URI:

    .. method:: Resource.get_single(self, request, objects, \*args, \**kwargs)
    .. method:: Resource.get_set(self, request, objects, \*args, \**kwargs)
    .. method:: Resource.get_page(self, request, objects, \*args, \**kwargs)

    These methods receive an :py:class:`Objects` instance containing all
    instances they have to process. The default implementation of all these
    methods use :py:meth:`API.serialize_instance` to do the serialization
    work (using the :py:class:`API` instance at :py:attr:`Resource.api`).

    If any of the referenced objects do not exist for the single and the set
    case, a HTTP 404 is returned instead of returning a partial response.

    The list URI does not only return a list of objects, but another mapping
    containing metadata about the response such as URIs for the previous and
    next page (if they exist) and the total object count.


.. method:: Resource.options(self, request, \*args, \**kwargs)

    Returns a list of allowed HTTP verbs in the ``Allow`` response header.
    The response is otherwise empty.

    .. note::

        URIs inside the resource might still return 405 Method not allowed
        erorrs if a particular HTTP verb is only implemented for a subset
        of URIs, for example only for single instances.


.. method:: Resource.post(self, request, \*args, \**kwargs)
.. method:: Resource.put(self, request, \*args, \**kwargs)
.. method:: Resource.delete(self, request, \*args, \**kwargs)
.. method:: Resource.patch(self, request, \*args, \**kwargs)
.. method:: Resource.trace(self, request, \*args, \**kwargs)

    Default implementations do not exist, that means that if you do not
    provide your own, the only answer will ever be a HTTP 405 Method not
    allowed error.


.. method:: Resource.serialize_response(self, response, status=httplib.OK, headers={})

    This method is a thin wrapper around :py:meth:`Serializer.serialize`.
    If ``response`` is already a :py:class:`~django.http.HttpResponse`
    instance, it is returned directly.

    The content types supported by :py:class:`Serializer` are JSON,
    but more on that later.



The serializer
==============

.. class:: Serializer()

The API supports output as JSON. The format is determined
by looking at the HTTP ``Accept`` header first. If no acceptable encoding
is found, a HTTP 406 Not acceptable error is returned to the client.

The detection of supported content types can be circumvented by adding
a querystring parameter naemd ``format``. The supported values are as
follows:

- ``?format=json`` or ``?format=application/json`` for JSON output


The request parser
==================

.. class:: RequestParser()

    Parses the request body into a format independent of its content type.

    Does nothing for the following HTTP methods because they are not supposed
    to have a request body:

    - ``GET``
    - ``HEAD``
    - ``OPTIONS``
    - ``TRACE``
    - ``DELETE``

    Otherwise, the code tries determining a parser for the request. The
    following content types are supported:

    - ``application/x-www-form-urlencoded`` (the default)
    - ``multipart/form-data``
    - ``application/json``

    The two former content types are supported directly by Django, all
    capabilities and restrictions are inherited directly. When using JSON,
    file uploads are not supported.

    The parsed data is available as ``request.POST`` and ``request.FILES``.
    ``request.POST`` is used instead of something else even for ``PUT`` and
    ``PATCH`` requests (among others), because most code written for Django
    expects data to be provided under that name.

    .. method:: RequestParser.parse(self, request)

        Decides whether the request body should be parsed, and if yes, decides
        which parser to use. Returns a HTTP 415 Unsupported media type if the
        request isn't understood.

    .. method:: RequestParser.parse_form(self, request)
    .. method:: RequestParser.parse_json(self, request)

        The actual work horses.


Additional classes and exceptions
=================================

.. exception:: APIException(error_message=None, status=None, data={})

    Custom exception which signals a problem detected somewhere inside
    the API machinery.

    Usage::

        # Use official W3C error names from ``httplib.responses``
        raise ClientError(status=httplib.NOT_ACCEPTABLE)

    or::

        raise ServerError('Not implemented, go away',
            status=httplib.NOT_IMPLEMENTED)

    Additional information can be passed through by setting the ``data``
    argument to a dict instance. The :py:exc:`APIException` handler
    will merge the dict into the default error data and return everything
    to the client::

        raise APIException('Validation failed', data={
            'form': form.errors,
            })


.. class:: Objects(queryset, page, set, single)

    A :py:class:`~collections.namedtuple` holding the return value of
    :py:meth:`Resource.objects`.

.. class:: Page(queryset, offset, limit, total)

    A :py:class:`~collections.namedtuple` for the ``page`` object from
    :py:class:`Objects` above.


Utility functions
=================

.. function:: api_reverse(model, ident, api_name='api', fail_silently=False, \**kwargs)

    Determines the canonical URL of API endpoints for arbitrary models.

    - ``model`` is the Django model you want to use,
    - ``ident`` should be one of ``list``, ``set`` or ``detail`` at the
      moment
    - Additional keyword arguments are forwarded to the
      :py:func:`~django.core.urlresolvers.reverse` call.

    Usage::

        api_reverse(Product, 'detail', pk=42)

    Passing an instance works too::

        api_reverse(instance, 'detail', pk=instance.pk)


.. function:: serialize_model_instance(instance, api, inline_depth=0, exclude=(), only_registered=True, build_absolute_uri=lambda uri: uri, \**kwargs)

    Serializes a single model instance.

    If ``inline_depth`` is a positive number, ``inline_depth`` levels of related
    objects are inlined. The performance implications of this feature might be
    severe! Note: Additional arguments specified when calling
    ``serialize_model_instance`` such as ``exclude``, ``only_registered`` and
    further keyword arguments are currently **not** forwarded to inlined
    objects. Those parameters should be set upon resource registration time as
    documented in the ``API`` docstring above.

    The ``exclude`` parameter is especially helpful when used together with
    ``functools.partial``.

    Set ``only_registered=False`` if you want to serialize models which do not
    have a canonical URI inside this API.

    ``build_absolute_uri`` should be a callable which transforms any passed
    URI fragment into an absolute URI including the protocol and the hostname,
    for example ``request.build_absolute_uri``.

    This implementation has a few characteristics you should be aware of:

    - Only objects which have a canonical URI inside this particular API are
      serialized; if no such URI exists, this method returns ``None``. This
      behavior can be overridden by passing ``only_registered=False``.
    - Many to many relations are only processed if ``inline_depth`` has a
      positive value. The reason for this design decision is that the database
      has to be queried for showing the URIs of related objects anyway and
      because of that we either show the full objects or nothing at all.
    - Some fields (currently only fields with choices) have a machine readable
      and a prettified value. The prettified values are delivered inside the
      ``__pretty__`` dictionary for your convenience.
    - The primary key of the model instance is always available as
      ``__pk__``.


.. function:: querystring(data, exclude=(), \**kwargs)

    Returns a properly encoded querystring

    The supported arguments are as follows:

    - ``data`` should be a ``MultiValueDict`` instance (i.e. ``request.GET``)
    - ``exclude`` is a list of keys from ``data`` which should be skipped
    - Additional key-value pairs are accepted as keyword arguments

    Usage::

        next_page_url = querystring(
            request.GET,
            exclude=('page',),
            page=current + 1,
            )


API behavior
============

Resource list
-------------

The available resources can be determined by sending a request to the root
URI of this API, ``/api/v1/``. Resources can either be canonical or not.

All resources are returned in a list, the canonical URIs for objects are
additionally returned as a hash.

The individual resources are described by a hash containing two values (as
do most objects returned by the API):

- ``__uri__``: The URI of the particular object
- ``__str__``: A string containing the 'name' of the object, whatever
  that would be (it's the return value of the ``__str__`` method for
  Django models, and the lowercased class name of the model registered
  with the resource).

In the list of resources, a particular ``__str__`` value will exist
several times if a model is exposed through more than one resource;
``__uri__`` values will always be unique.


Listing endpoints
-----------------

All API endpoints currently support GET, HEAD and OPTIONS requests.

All listing endpoints support the following parameters:

- ``?limit=<integer>``: Determines how many objects will be shown on a
  single page. The default value is 20. The lower limit is zero, the
  upper limit is determined by the variable ``max_limit_per_page`` which
  defaults to 1000.
- ``?offset=<integer>``: Can be used for retrieving a different page
  of objects. Passing ``?offset=20`` with a limit of 20 will return the
  next page. The offset is zero-indexed.

.. note::

   You won't have to construct query strings containing these parameters
   yourself in most cases. All list views return a mapping with additional
   information about the current request and ``next`` and ``previous``
   links for your convenience as well.


List views return two data structures, ``objects`` and ``meta``. The
former is a list of all objects for the current request, the latter
a mapping of additional information about the current set of objects:

- ``offset``: The offset value as described above.
- ``limit``: The limit value as described above.
- ``total``: The total count of objects.
- ``previous``: A link to the previous page or ``null``.
- ``next``: A link to the next page or ``null``.


Object representation
---------------------

The following fields should always be available on objects returned:

- ``__uri__``: The URI.
- ``__pk__``: The primary key of this object.
- ``__str__``: The return value of the ``__str__`` or ``__unicode__``
  method.

A few fields' values have to be treated specially, because their values
do not have an obvious representation in an JSON document. The fields and
their representations are as follows:

- :py:class:`~datetime.date` and :py:class:`~datetime.datetime` objects
  are converted into strings using :py:func:`str`.
- :py:class:`~decimal.Decimal` is converted into a string without (lossy)
  conversion to :py:class:`float <types.FloatType>` first.
- :py:class:`~django.db.models.FileField` and
  :py:class:`~django.db.models.ImageField` are shown as the URL of the
  file.
- :py:class:`~django.db.models.ForeignKey` fields are shown as their
  canonical URI (if there exists such a URI inside this API) or even
  inlined if ``?full=1`` is passed when requesting the details of an
  object.
