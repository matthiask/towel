from collections import namedtuple
from datetime import date, datetime
from decimal import Decimal
import httplib
import json
from lxml.etree import Element, SubElement, tostring
import mimeparse
import operator
from urllib import urlencode

from django.conf.urls import patterns, include, url
from django.core.serializers.json import DjangoJSONEncoder
from django.core.urlresolvers import NoReverseMatch, reverse
from django.db import models
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.cache import patch_vary_headers
from django.utils.functional import curry
from django.views import generic
from django.views.decorators.csrf import csrf_exempt


class APIException(Exception):
    """
    Custom exception which signals a problem detected somewhere inside
    the API machinery.

    Usage::

        # Use official W3C error names from ``httplib.responses``
        raise ClientError(status=httplib.NOT_ACCEPTABLE)

    or::

        raise ServerError('Not implemented, go away',
            status=httplib.NOT_IMPLEMENTED)

    Additional information can be passed through by setting the ``data``
    argument to a dict instance. The :py:exc:`~towel.api.APIException` handler
    will merge the dict into the default error data and return everything
    to the client::

        raise APIException('Validation failed', data={
            'form': form.errors,
            })
    """

    #: The default response is '400 Bad request'
    default_status = httplib.BAD_REQUEST

    def __init__(self, error_message=None, status=None, data={}):
        super(Exception, self).__init__(error_message)

        self.status = self.default_status if status is None else status
        if error_message is None:
            self.error_message = httplib.responses.get(self.status, '')
        else:
            self.error_message = error_message

        self.data = data


#: The return value of ``Resource.objects``
Objects = namedtuple('Objects', 'queryset page set single')


#: The ``page`` object from ``Resource.objects``
Page = namedtuple('Page', 'queryset offset limit total')


class API(object):
    """
    This is the main API object. It does not do much except give an overview
    over all resources. It will hold the necessary bits to have more than one
    API with the same models or resources at the same time (f.e. versions).

    Usage::

        # ... other imports ...
        from functools import partial
        from towel.api import API, serialize_model_instance

        api_v1 = API('v1')

        # Customize serialization: Never include phone numbers and email
        # addresses of customers in API output.
        api_v1.register(
            Customer,
            serializer=partial(serialize_model_instance,
                exclude=('phone', 'email')),
            view_init={
                'queryset': Customer.objects.filter(is_active=True),
                })

        api_v1.register(
            Product,
            view_init={
                'queryset': Product.objects.filter(is_active=True)
                })

        api_v1.register(
            Product,
            canonical=False,
            prefix=r'^library/',
            view_class=LibraryResource,
            view_init={
                'queryset': Product.objects.filter(is_active=True),
                })

        urlpatterns = patterns('',
            url(r'^v1/', include(api_v1.urls)),
        )

    With authentication::

        api_v2 = API('v2', decorators=[csrf_exempt, login_required])

        # register resources as before
    """

    def __init__(self, name, decorators=[csrf_exempt]):
        self.name = name
        self.decorators = decorators

        self.resources = []
        self.serializers = {}
        self.views = []

    @property
    def urls(self):
        """
        Inclusion point in your own URLconf

        Usage::

            from .views import api_v1

            urlpatterns = patterns('',
                url(r'^api/v1/', include(api_v1.urls)),
            )
        """

        def view(request):
            return self.root(request)
        for dec in reversed(self.decorators):
            view = dec(view)

        urlpatterns = [
            url(r'^$', view, name='api_%s' % self.name),
            ]

        for view in self.views:
            urlpatterns.append(url(view['prefix'], view['view']))

        for resource in self.resources:
            urlpatterns.append(url(
                resource['prefix'],
                include(resource['urlpatterns']),
                ))

        return patterns('', *urlpatterns)

    def root(self, request):
        """
        Main API view, returns a list of all available resources
        """
        if request.method == 'OPTIONS':
            response = HttpResponse()
            response['Allow'] = 'GET, HEAD'
            response['Content-Length'] = 0
            return response

        elif request.method not in ('GET', 'HEAD'):
            return Serializer().serialize({
                'error': 'Not acceptable',
                }, request=request, status=httplib.METHOD_NOT_ALLOWED,
                output_format=request.GET.get('format'))

        response = {
            '__unicode__': self.name,
            '__uri__': request.build_absolute_uri(reverse('api_%s' % self.name)),
            'resources': [],
            }

        for view in self.views:
            response.setdefault('views', []).append({
                '__unicode__': view['prefix'].strip('^').strip('/'),
                '__uri__': request.build_absolute_uri(u''.join((
                    response['__uri__'],
                    view['prefix'].strip('^')))),
                })

        for resource in self.resources:
            r = {
                '__unicode__': resource['model'].__name__.lower(),
                '__uri__': request.build_absolute_uri(u''.join((
                    response['__uri__'],
                    resource['prefix'].strip('^')))),
                }

            response['resources'].append(r)
            if resource['canonical']:
                response[resource['model'].__name__.lower()] = r

        return Serializer().serialize(response, request=request,
            output_format=request.GET.get('format'))

    def register(self, model, view_class=None, canonical=True,
            decorators=None, prefix=None, view_init=None,
            serializer=None):
        """
        Registers another resource on this API. The sole required argument is
        the Django model which should be exposed. The other arguments are:

        - ``view_class``: The resource view class used, defaults to
          :class:`towel.api.Resource`.
        - ``canonical``: Whether this resource is the canonical location of
          the model in this API. Allows registering the same model several
          times in the API (only one location should be the canonical
          location!)
        - ``decorators``: A list of decorators which should be applied to the
          view. Function decorators only, method decorators aren't supported.
          The list is applied in reverse, the order is therefore the same as
          with the ``@`` notation. If unset, the set of decorators is
          determined from the API initialization. Pass an empty list if you
          want no decorators at all. Otherwise API POSTing will have to
          include a valid CSRF middleware token.
        - ``prefix``: The prefix for this model, defaults to the model name in
          lowercase. You should include a caret and a trailing slash if you
          specify this yourself (``prefix=r'^library/'``).
        - ``view_init``: Python dictionary which contains keyword arguments
          used during the instantiation of the ``view_class``.
        - ``serializer``: Function which takes a model instance, the API
          instance and additional keyword arguments (accept ``**kwargs`` for
          forward compatibility) and returns the serialized representation as
          a Python dict.
        """

        view_class = view_class or Resource
        view_init = view_init or {}

        if 'model' not in view_init:
            if 'queryset' in view_init:
                view_init['model'] = view_init['queryset'].model
            else:
                view_init['model'] = model

        view = view_class.as_view(api=self, **view_init)

        name = lambda ident: None
        if canonical:
            opts = model._meta
            name = lambda ident: '_'.join((
                self.name, opts.app_label, opts.module_name, ident))

        if decorators is None:
            decorators = self.decorators

        if decorators:
            for dec in reversed(decorators):
                view = dec(view)

        self.resources.append({
            'model': model,
            'canonical': canonical,
            'prefix': prefix or r'^%s/' % model.__name__.lower(),
            'urlpatterns': patterns('',
                url(r'^$', view, name=name('list')),
                url(r'^(?P<pk>\d+)/$', view, name=name('detail')),
                url(r'^(?P<pks>(?:\d+;)*\d+);?/$', view, name=name('set')),
                ),
            })

        if serializer:
            self.serializers[model] = serializer

    def serialize_instance(self, instance, **kwargs):
        """
        Returns a serialized version of the passed model instance

        This method should always be used for serialization, because it knows
        about custom serializers specified when registering resources with
        this API.
        """
        serializer = self.serializers.get(instance.__class__,
            serialize_model_instance)
        return serializer(instance, api=self, **kwargs)

    def add_view(self, view, prefix=None, decorators=None):
        """
        Add custom views to this API

        The prefix is automatically determined if not given based on the
        function name.

        The view receives an additional keyword argument ``api`` containing
        the API instance.
        """

        prefix = prefix or r'^%s/' % view.__name__

        if decorators is None:
            decorators = self.decorators

        view = curry(view, api=self)
        for dec in reversed(decorators):
            view = dec(view)

        self.views.append({
            'prefix': prefix,
            'view': view,
            })


def serialize_model_instance(instance, api, inline_depth=0, exclude=(),
        only_registered=True, build_absolute_uri=lambda uri: uri,
        **kwargs):
    """
    Serializes a single model instance.

    If ``inline_depth`` is a positive number, ``inline_depth`` levels of
    related objects are inlined. The performance implications of this feature
    might be severe! Note: Additional arguments specified when calling
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
    """

    # It's not exactly a fatal error, but it helps during development. This
    # statement will disappear in the future.
    assert not kwargs, 'Unknown keyword arguments to serialize_model_instance'

    uri = api_reverse(instance, 'detail', api_name=api.name,
        pk=instance.pk, fail_silently=True)

    if uri is None and only_registered:
        return None

    data = {
        '__uri__': build_absolute_uri(uri),
        '__unicode__': unicode(instance),
        '__pretty__': {},
        '__pk__': instance.pk,
        }
    opts = instance._meta

    for f in opts.fields:
        if f.name in exclude:
            continue

        if f.rel:
            try:
                data[f.name] = build_absolute_uri(api_reverse(
                    f.rel.to,
                    'detail',
                    api_name=api.name,
                    pk=f.value_from_object(instance)))
            except NoReverseMatch:
                if only_registered:
                    continue

            if inline_depth > 0:
                related = getattr(instance, f.name)

                if related:
                    # XXX What about only_registered, kwargs? Should they be
                    # passed to other calls as well, or should we assume that
                    # customization can only happen using functools.partial
                    # upon registration time?
                    data[f.name] = api.serialize_instance(
                        related,
                        inline_depth=inline_depth - 1,
                        build_absolute_uri=build_absolute_uri,
                        )

        elif isinstance(f, models.FileField):
            # XXX add additional informations to the seralization?
            try:
                value = f.value_from_object(instance)
                data[f.name] = build_absolute_uri(value.url)
            except ValueError:
                data[f.name] = ''

        else:
            data[f.name] = f.value_from_object(instance)

            if f.flatchoices:
                data['__pretty__'][f.name] = unicode(
                    dict(f.flatchoices).get(data[f.name], '-'))

    if inline_depth > 0:
        for f in opts.many_to_many:
            if f.name in exclude:
                continue

            related = [
                api.serialize_instance(
                    obj,
                    inline_depth=inline_depth - 1,
                    build_absolute_uri=build_absolute_uri,
                ) for obj in getattr(instance, f.name).all()]

            if any(related):
                data[f.name] = related

    return data


def api_reverse(model, ident, api_name='api', fail_silently=False, **kwargs):
    """
    Determines the canonical URL of API endpoints for arbitrary models

    ``model`` is the Django model you want to use, ident should be one of
    ``list``, ``set`` or ``detail`` at the moment, additional keyword arguments
    are forwarded to the ``django.core.urlresolvers.reverse`` call.

    Usage::

        api_reverse(Product, 'detail', pk=42)

    Passing an instance works too::

        api_reverse(instance, 'detail', pk=instance.pk)
    """
    opts = model._meta
    try:
        return reverse(
            '_'.join((api_name, opts.app_label, opts.module_name, ident)),
            kwargs=kwargs)
    except NoReverseMatch:
        if fail_silently:
            return None
        raise


class Serializer(object):
    """
    API response serializer

    Handles content type negotiation using the HTTP Accept header if the format
    isn't overridden.
    """
    def serialize(self, data, output_format=None, request=None,
            status=httplib.OK, headers={}):
        """
        Returns a ``HttpResponse`` containing the serialized response in the
        format specified explicitly in ``output_format`` (either as a MIME type
        or as a simple identifier) or according to the HTTP Accept header
        specified in the passed request instance. The default status code is
        ``200 OK``, if that does not fit you'll have to specify a different
        code yourself.

        Returns a ``406 Not acceptable`` response if the requested format is
        unknown or unsupported. Currently, the following formats are supported:

        - ``json`` or ``application/json``
        - ``xml`` or ``application/xml``

        Usage::

            return Serializer().serialize(
                {'response': 'Hello world'},
                output_format='xml',
                status=httplib.OK)

        or::

            return Serializer().serialize(
                {'response': 'Hello world'},
                output_format='application/json',
                status=httplib.OK)

        or::

            return Serializer().serialize(
                {'response': 'Hello world'},
                request=request,
                status=httplib.OK)
        """
        if output_format is None and request is None:
            raise TypeError(
                'Provide at least one of output_format and request.')

        if output_format is None:
            # Thanks django-tastypie!
            try:
                output_format = mimeparse.best_match(reversed([
                    'application/xml',
                    'application/json',
                    ]),
                    request.META.get('HTTP_ACCEPT'))
            except IndexError:
                pass

        if output_format in ('application/json', 'json'):
            response = self.to_json(data)

        elif output_format in ('application/xml', 'xml'):
            response = self.to_xml(data)

        else:
            # Cannot raise ClientError here because the APIException handler
            # calls into this method too.
            response = HttpResponse('Not acceptable')
            status = httplib.NOT_ACCEPTABLE

        for key, value in headers.iteritems():
            response[key] = value

        patch_vary_headers(response, ('Accept',))
        response.status_code = status
        return response

    def to_json(self, data):
        return HttpResponse(
            json.dumps(data, cls=DjangoJSONEncoder),
            mimetype='application/json',
            )

    def to_xml(self, data):
        valuetypes = {
            int: 'integer',
            long: 'integer',
            float: 'float',
            Decimal: 'decimal',
            bool: 'boolean',
            list: 'list',
            tuple: 'tuple',
            dict: 'hash',
            basestring: 'string',
            str: 'string',
            unicode: 'string',
            date: 'date',
            datetime: 'datetime',
            }
        valuetypes_tuple = tuple(valuetypes.keys())

        def _serialize(parent, data, name=''):
            if isinstance(data, dict):
                object = SubElement(parent, 'object', attrib={
                    'name': name,
                    'type': 'hash',
                    })
                for key, value in data.iteritems():
                    _serialize(object, value, name=key)

            elif hasattr(data, '__iter__'):
                objects = SubElement(parent, 'objects', {
                    'name': name,
                    'type': 'list',
                    })
                for value in data:
                    _serialize(objects, value)

            elif isinstance(data, valuetypes_tuple):
                value = SubElement(parent, 'value', attrib={
                    'name': name,
                    'type': valuetypes.get(type(data), 'unknown'),
                    })

                value.text = (data if isinstance(data, basestring)
                    else unicode(data))

            elif data is None:
                SubElement(parent, 'value', attrib={
                    'name': name,
                    'type': 'null',
                    })

            else:
                raise NotImplementedError('Unable to handle %r' % data)

        root = Element('response')
        for key, value in data.iteritems():
            _serialize(root, value, name=key)

        return HttpResponse(
            tostring(root, xml_declaration=True, encoding='utf-8'),
            mimetype='application/xml',
            )


class Resource(generic.View):
    """
    Resource for exposing Django models somewhat RESTy
    """

    #: The API to which this resource is bound to.
    api = None

    #: The model exposed by this resource.
    model = None

    #: Prefiltered queryset for this resource. Defaults to
    #:``model._default_manager.all()`` if unset.
    queryset = None

    #: Default instance count for list views
    limit_per_page = 20
    #: Higher values than this will not be accepted for ``limit``
    max_limit_per_page = 1000

    #: Almost the same as ``django.views.generic.View.http_method_names`` but
    #: not quite, we allow ``patch`` as well.
    http_method_names = ['get', 'post', 'put', 'delete', 'head', 'patch',
        'options', 'trace']

    def dispatch(self, request, *args, **kwargs):
        """
        This method is almost the same as Django's own
        ``generic.View.dispatch()``, but there are a few subtle differences:

        - It uses ``self.request``, ``self.args`` and ``self.kwargs`` in all
          places
        - It calls ``self.unserialize_request()`` after assigning the
          aforementioned variables on ``self`` which may modify all aspects and
          all variables (f.e.  deserialize a JSON request and serialize it
          again to look like a standard POST request) and only then determines
          whether the request should be handled by this view at all.
        - The return value of the ``get()``, ``post()`` etc. methods is passed
          to ``self.serialize_response()`` and only then returned to the
          client. The processing methods should return data (a ``dict``
          instance most of the time) which is then serialized into the
          requested format or some different supported format.
        """
        self.request = request
        self.args = args
        self.kwargs = kwargs
        self.unserialize_request()

        # Try to dispatch to the right method; if a method doesn't exist,
        # defer to the error handler. Also defer to the error handler if the
        # request method isn't on the approved list.
        method = self.request.method.lower()
        if not (method in self.http_method_names and hasattr(self, method)):
            handler = self.http_method_not_allowed
        else:
            handler = getattr(self, method)

        try:
            return self.serialize_response(handler(
                self.request, *self.args, **self.kwargs))
        except Http404 as e:
            return self.serialize_response({'error': e[0]},
                status=httplib.NOT_FOUND)
        except APIException as e:
            data = {
                'error': e.error_message,
                }
            data.update(e.data)
            return self.serialize_response(data, status=e.status)

    def unserialize_request(self):
        """
        This method standardizes various aspects of the incoming request, f.e.
        decoding of JSON requests etc.

        The "real" processing methods should not have to distinguish between
        varying request types anymore.
        """
        # TODO Actually implement this :-)
        pass

    def serialize_response(self, response, status=httplib.OK, headers={}):
        """
        Serializes the response into an appropriate format for the wire such
        as JSON. ``HttpResponse`` instances are returned directly.
        """
        if isinstance(response, HttpResponse):
            return response

        return Serializer().serialize(response, request=self.request,
            status=status, output_format=self.request.GET.get('format'),
            headers=headers)

    def get_query_set(self):
        """
        Returns the queryset used by this resource. If you need access or
        visibility control, add it here.
        """
        if self.queryset:
            return self.queryset._clone()
        elif self.model:
            return self.model._default_manager.all()

    def apply_filters(self, queryset):
        """
        Applies filters and search queries to the queryset. This method will
        only be called for list views, not when the user requested sets or
        single instances.
        """
        return queryset

    def objects(self):
        """
        Returns a ``namedtuple`` with the following attributes:

        - ``queryset``: Available items, filtered and all (if applicable).
        - ``page``: Current page
        - ``set``: List of objects or ``None`` if not applicable. Will be used
          for requests such as ``/api/product/1;3/``.
        - ``single``: Single instances if applicable, used for URIs such as
          ``/api/product/1/``.

        Raises a ``Http404`` exception if the referenced items do not exist in
        the queryset returned by ``Resource.get_query_set()``.
        """
        queryset, page, set_, single = self.get_query_set(), None, None, None

        if 'pk' in self.kwargs:
            single = get_object_or_404(queryset, pk=self.kwargs['pk'])

        elif 'pks' in self.kwargs:
            pks = set(pk for pk in self.kwargs['pks'].split(';') if pk)
            set_ = queryset.in_bulk(pks).values()

            if len(pks) != len(set_):
                raise Http404('Some objects do not exist.')

        else:
            queryset = self.apply_filters(queryset)

            try:
                offset = int(self.request.GET.get('offset'))
            except (TypeError, ValueError):
                offset = 0

            try:
                limit = int(self.request.GET.get('limit'))
            except (TypeError, ValueError):
                limit = self.limit_per_page

            # Do not allow more than max_limit_per_page entries in one request,
            # ever
            limit = min(limit, self.max_limit_per_page)

            # Sanitize range
            offset = max(offset, 0)
            limit = max(limit, 0)

            page = Page(
                queryset[offset:offset + limit],
                offset,
                limit,
                queryset.count(),
                )

        return Objects(queryset, page, set_, single)

    def get(self, request, *args, **kwargs):
        """
        Processes GET requests by returning lists, sets or detail data. All of
        these URLs are supported by this implementation:

        - ``resource/``: Paginated list of objects, first page
        - ``resource/?page=3``: Paginated list of objects, third page
        - ``resource/42/``: Object with primary key of 42
        - ``resource/1;3;5/``: Set of the three objects with a primary key of
          1, 3 and 5. The last item may have a semicolon too for simplicity, it
          will be ignored. The following URI would be equivalent:
          ``resource/1;;3;5;`` (but it is bad style).

        Filtering or searching is not supported at the moment.
        """
        objects = self.objects()

        if objects.single:
            return self.get_single(request, objects, *args, **kwargs)
        elif objects.set:
            return self.get_set(request, objects, *args, **kwargs)
        else:
            return self.get_page(request, objects, *args, **kwargs)

    def get_single(self, request, objects, *args, **kwargs):
        kw = {}
        if request.GET.get('full'):
            kw['inline_depth'] = 1
        return self.api.serialize_instance(
            objects.single,
            build_absolute_uri=request.build_absolute_uri,
            **kw)

    def get_set(self, request, objects, *args, **kwargs):
        return {
            'objects': [
                self.api.serialize_instance(
                    instance,
                    build_absolute_uri=request.build_absolute_uri,
                    ) for instance in objects.set],
            }

    def get_page(self, request, objects, *args, **kwargs):
        page = objects.page
        list_url = api_reverse(objects.queryset.model, 'list',
            api_name=self.api.name)
        meta = {
            'offset': page.offset,
            'limit': page.limit,
            'total': page.total,
            'previous': None,
            'next': None,
            }

        if page.offset > 0:
            meta['previous'] = u'%s?%s' % (list_url, querystring(
                self.request.GET,
                exclude=('offset', 'limit'),
                offset=max(0, page.offset - page.limit),
                limit=page.limit,
                ))

        if page.offset + page.limit < page.total:
            meta['next'] = u'%s?%s' % (list_url, querystring(
                self.request.GET,
                exclude=('offset', 'limit'),
                offset=page.offset + page.limit,
                limit=page.limit,
                ))

        return {
            'objects': [
                self.api.serialize_instance(
                    instance,
                    build_absolute_uri=request.build_absolute_uri,
                    ) for instance in page.queryset],
            'meta': meta,
            }

    def options(self, request, *args, **kwargs):
        # XXX This will be removed as soon as we switch to Django 1.5 only
        response = HttpResponse()
        response['Allow'] = ', '.join(self._allowed_methods())
        response['Content-Length'] = 0
        return response

    def _allowed_methods(self):
        return [m.upper() for m in self.http_method_names if hasattr(self, m)]


def querystring(data, exclude=(), **kwargs):
    """
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
    """
    items = reduce(operator.add, (
        list((k, v.encode('utf-8')) for v in values)
        for k, values in data.iterlists() if k not in exclude
        ), [])

    for k, v in kwargs.iteritems():
        items.append((k, unicode(v).encode('utf-8')))

    return urlencode(items)
