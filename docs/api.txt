Towel API
*********


Content types
=============

This section explains which content types / mimetypes are supported by
the API as request and response data.


Request data
------------

Request data is currently only accepted in two forms:

- urlencoded in the request body
- multipart in the request body


Response data
-------------

The API supports output as XML or as JSON. The format is determined
by looking at the HTTP ``Accept`` header first. If no acceptable encoding
is found, a ``HTTP 406 Not acceptable`` error is returned to the client.

The detection of supported content types can be circumvented by adding
a querystring parameter naemd ``format``. The supported values are as
follows:

- ``?format=json`` or ``?format=application/json`` for JSON output
- ``?format=xml`` or ``?format=application/xml`` for XML output


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
- ``__unicode__``: A string containing the 'name' of the object, whatever
  that would be (it's the return value of the ``__unicode__`` method for
  Django models, and the lowercased class name of the model registered
  with the resource).

In the list of resources, a particular ``__unicode__`` value will exist
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
- ``__unicode__``: The return value of the ``__unicode__`` method.

A few fields' values have to be treated specially, because their values
do not have an obvious representation in an XML or JSON document. The
fields and their representations are as follows:

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
