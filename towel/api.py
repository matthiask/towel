from collections import namedtuple
import json
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
from django.views import generic
from django.views.decorators.csrf import csrf_exempt


class APIException(Exception):
    """
    Custom exception which signals a problem detected somewhere inside
    the API machinery.

    Usage::

        raise ClientError('Not acceptable', status=406)

    or::

        raise ServerError('Not implemented, go away', status=501)
    """
    default_status = 400

    def __init__(self, error, **kwargs):
        super(Exception, self).__init__(error)
        self.kwargs = kwargs


class ClientError(APIException):
    pass

class ServerError(APIException):
    default_status = 500


#: The return value of ``Resource.objects``
Objects = namedtuple('Objects', 'queryset page set single')

#: The ``page`` object from ``Resource.objects``
Page = namedtuple('Page', 'queryset offset limit total')


class API(object):
    """
    This is the main API object. It does not do much except give an overview over
    all resources. It will hold the necessary bits to have more than one API
    with the same models or resources at the same time (f.e. versions).

    Usage::

        api_v1 = API('v1')

        api_v1.register(
            Customer,
            view_init={
                'queryset': Customer.objects.filter(is_active=True),
                'paginate_by': 10,
                })

        api_v1.register(
            Product,
            view_init={
                'queryset': Product.objects.filter(is_active=True)
                'paginate_by': 10,
                })

        api_v1.register(
            Product,
            canonical=False,
            prefix=r'^library/',
            view_class=LibraryResource,
            view_init={
                'queryset': Product.objects.filter(is_active=True),
                'paginate_by': 10,
                })

        urlpatterns = patterns('',
            url(r'^v1/', include(api_v1.urls)),
        )
    """

    def __init__(self, name):
        self.name = name
        self.resources = []
        self.serializers = {}

    @property
    def urls(self):
        """
        Inclusion point in your own URLconf

        Pass the return value to ``include()``.
        """
        urlpatterns = [
            url(r'^$', self, name='api_%s' % self.name),
            ]

        for resource in self.resources:
            urlpatterns.append(url(
                resource['prefix'],
                include(resource['urlpatterns']),
                ))

        return patterns('', *urlpatterns)

    def __call__(self, request):
        """
        Main API view, returns a list of all available resources
        """
        response = {
            '__unicode__': self.name,
            '__uri__': reverse('api_%s' % self.name),
            'resources': [],
            }

        for resource in self.resources:
            r = {
                '__unicode__': resource['model'].__name__.lower(),
                '__uri__': u''.join((response['__uri__'], resource['prefix'].strip('^'))),
                }

            response['resources'].append(r)
            if resource['canonical']:
                response[resource['model'].__name__.lower()] = r

        # TODO content negotiation :-(
        return HttpResponse(json.dumps(response), mimetype='application/json')

    def register(self, model, view_class=None, canonical=True,
            decorators=[csrf_exempt], prefix=None, view_init=None,
            serializer=None):
        """
        Registers another resource on this API. The sole required argument is the
        Django model which should be exposed. The other arguments are:

        - ``view_class``: The resource view class used, defaults to
          :class:`towel.api.Resource`.
        - ``canonical``: Whether this resource is the canonical location of the
          model in this API. Allows registering the same model several times in
          the API (only one location should be the canonical location!)
        - ``decorators``: A list of decorators which should be applied to the
          view. Function decorators only, method decorators aren't supported. The
          list is applied in reverse, the order is therefore the same as with the
          ``@`` notation. It's recommended to always pass ``csrf_exempt`` here,
          otherwise API POSTing will have to include a valid CSRF middleware token.
        - ``prefix``: The prefix for this model, defaults to the model name in
          lowercase. You should include a caret and a trailing slash if you specify
          this yourself (``prefix=r'^library/'``).
        - ``view_init``: Python dictionary which contains keyword arguments used
          during the instantiation of the ``view_class``.
        - ``serializer``: Function which takes a model instance, the API instance
          and additional keyword arguments (accept ``**kwargs`` for forward
          compatibility) and returns the serialized representation as a Python dict.
        """

        view_class = view_class or Resource
        view_init = view_init or {}

        if 'model' not in view_init:
            view_init['model'] = view_init.get('queryset').model or model

        view = view_class.as_view(api=self, **view_init)

        name = lambda ident: None
        if canonical:
            opts = model._meta
            name = lambda ident: '_'.join((
                self.name, opts.app_label, opts.module_name, ident))

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
        serializer = self.serializers.get(instance.__class__, serialize_model_instance)
        return serializer(instance, api=self, **kwargs)


def serialize_model_instance(instance, api, inline_depth=0, exclude=(), **kwargs):
    """
    Serializes a single model instance.

    If ``inline_depth`` is a positive number, ``inline_depth`` levels of related
    objects are inlined. The performance implications of this feature might be
    severe!

    The ``exclude`` parameter is especially helpful when used together with
    ``functools.partial``.

    This implementation has a few characteristics you should be aware of:

    - Only objects which have a canonical URI inside this particular API are
      serialized; if no such URI exists, this method returns ``None``.
    - Many to many relations are only processed if ``inline_depth`` has a
      positive value. The reason for this design decision is that the database
      has to be queried for showing the URIs of related objects anyway and
      because of that we either show the full objects or nothing at all.
    - Some fields (currently only fields with choices) have a machine readable
      and a prettified value. The prettified values are delivered inside the
      ``__pretty__`` dictionary for your convenience.
    """

    # It's not exactly a fatal error, but it helps during development. This
    # statement will disappear in the future.
    assert not kwargs, 'Unknown keyword arguments to serialize_model_instance'

    uri = api_reverse(instance, 'detail', api_name=api.name,
        pk=instance.pk, fail_silently=True)

    if uri is None:
        return None

    data = {
        '__uri__': uri,
        '__unicode__': unicode(instance),
        '__pretty__': {},
        }
    opts = instance._meta

    for f in opts.fields:
        if f.name in exclude:
            continue

        if f.rel:
            if inline_depth > 0:
                if getattr(instance, f.name):
                    data[f.name] = api.serialize_instance(
                        getattr(instance, f.name),
                        inline_depth=inline_depth-1,
                        )
                else:
                    data[f.name] = None

            else:
                try:
                    data[f.name] = api_reverse(f.rel.to, 'detail', api_name=api.name,
                        pk=f.value_from_object(instance))
                except NoReverseMatch:
                    continue

        elif isinstance(f, models.FileField):
            # XXX add additional informations to the seralization?
            value = f.value_from_object(instance)
            data[f.name] = value.url

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
                api.serialize_instance(obj, inline_depth=inline_depth-1)
                for obj in getattr(instance, f.name).all()]

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
        return reverse('_'.join((api_name, opts.app_label, opts.module_name, ident)),
            kwargs=kwargs)
    except NoReverseMatch:
        if fail_silently:
            return None
        raise


class Resource(generic.View):
    """
    Resource for exposing Django models somewhat RESTy
    """

    #: The API to which this resource is bound to.
    api = None

    #: The model exposed by this resource.
    model = None

    #: Prefiltered queryset for this resource. Defaults to ``model._default_manager.all()``
    #: if unset.
    queryset = None

    #: Limits
    limit_per_page = 20
    max_limit_per_page = 1000

    #: Almost the same as ``django.views.generic.View.http_method_names`` but not quite,
    #: we allow ``patch``, but do not allow ``options`` and ``trace``.
    http_method_names = ['get', 'post', 'put', 'delete', 'head', 'patch']

    def dispatch(self, request, *args, **kwargs):
        """
        This method is almost the same as Django's own ``generic.View.dispatch()``,
        but there are a few subtle differences:

        - It uses ``self.request``, ``self.args`` and ``self.kwargs`` in all places
        - It calls ``self.unserialize_request()`` after assigning the aforementioned
          variables on ``self`` which may modify all aspects and all variables (f.e.
          deserialize a JSON request and serialize it again to look like a standard
          POST request) and only then determines whether the request should be handled
          by this view at all.
        - The return value of the ``get()``, ``post()`` etc. methods is passed to
          ``self.serialize_response()`` and only then returned to the client. The
          processing methods should return data (a ``dict`` instance most of the time)
          which is then serialized into the requested format or some different supported
          format.
        """
        self.request = request
        self.args = args
        self.kwargs = kwargs
        self.unserialize_request()

        # Try to dispatch to the right method; if a method doesn't exist,
        # defer to the error handler. Also defer to the error handler if the
        # request method isn't on the approved list.
        if self.request.method.lower() in self.http_method_names:
            handler = getattr(self, self.request.method.lower(), self.http_method_not_allowed)
        else:
            handler = self.http_method_not_allowed

        try:
            return self.serialize_response(handler(
                self.request, *self.args, **self.kwargs))
        except Http404 as e:
            return self.serialize_response({'error': e[0]}, status=404)
        except APIException as e:
            return self.serialize_response({'error': e[0]},
                status=e.kwargs.get('status', e.default_status))

    def unserialize_request(self):
        """
        This method standardizes various aspects of the incoming request, f.e.
        decoding of JSON requests etc.

        The "real" processing methods should not have to distinguish between
        varying request types anymore.
        """
        pass

    def serialize_response(self, response, status=200):
        """
        Serializes the response into an appropriate format for the wire such as
        JSON. ``HttpResponse`` instances are returned directly.
        """
        if isinstance(response, HttpResponse):
            return response

        formats = [
            ('application/json', {
                'handler': lambda response, output_format, config: (
                    HttpResponse(json.dumps(response, cls=DjangoJSONEncoder),
                        mimetype='application/json', status=status)),
                }),
            #('text/html', {
                #'handler': self.serialize_response_html,
                #}),
            ]

        # Thanks!
        # https://github.com/toastdriven/django-tastypie/blob/master/tastypie/utils/mime.py
        try:
            output_format = mimeparse.best_match(
                reversed([format for format, config in formats]),
                self.request.META.get('HTTP_ACCEPT'))
        except IndexError:
            output_format = 'application/json'

        config = dict(formats)[output_format]
        response = config['handler'](response, output_format, config)
        patch_vary_headers(response, ('Accept',))
        return response

    def get_query_set(self):
        """
        Returns the queryset used by this resource. If you need access or visibility control,
        add it here.
        """
        if self.queryset:
            return self.queryset._clone()
        elif self.model:
            return self.model._default_manager.all()

    def apply_filters(self, queryset):
        """
        Applies filters to the queryset. This method will only be called for
        list views, not when the user requested sets or single instances.
        """
        return queryset

    def objects(self):
        """
        Returns a namedtuple with the following attributes:

        - ``queryset``: Available items, filtered and all (if applicable).
        - ``page``: Current page
        - ``set``: List of objects or ``None`` if not applicable. Will be used for
          requests such as ``/api/product/1;3/``.
        - ``single``: Single instances if applicable, used for URIs such as
          ``/api/product/1/``.

        Raises a 404 if the referenced items do not exist.
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

            # Do not allow more than max_limit_per_page entries in one request, ever
            limit = min(limit, self.max_limit_per_page)

            # Sanitize range
            offset = max(offset, 0)
            limit = max(limit, 0)

            page = Page(
                queryset[offset:offset+limit],
                offset,
                limit,
                queryset.count(),
                )

        return Objects(queryset, page, set_, single)

    def get(self, request, *args, **kwargs):
        """
        Processes GET requests by returning lists, sets or detail data. All of these
        URLs are supported by this implementation:

        - ``resource/``: Paginated list of objects, first page
        - ``resource/?page=3``: Paginated list of objects, third page
        - ``resource/42/``: Object with primary key of 42
        - ``resource/1;3;5/``: Set of the three objects with a primary key of
          1, 3 and 5. The last item may have a semicolon too for simplicity, it
          will be ignored. The following URI would be equivalent: ``resource/1;;3;5;``
          (but it is bad style).

        Filtering or searching is not supported at the moment.
        """
        objects = self.objects()

        if objects.single:
            return self.api.serialize_instance(objects.single,
                inline_depth=1 if request.GET.get('full') else 0)
        elif objects.set:
            return {
                'objects': [self.api.serialize_instance(instance) for instance in objects.set],
                }
        else:
            page = objects.page
            list_url = api_reverse(objects.queryset.model, 'list', api_name=self.api.name)
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
                'objects': [self.api.serialize_instance(instance) for instance in page.queryset],
                'meta': meta,
                }


def querystring(data, exclude=(), **kwargs):
    items = reduce(operator.add, (
        list((k, v.encode('utf-8')) for v in values)
        for k, values in data.iterlists() if k not in exclude
        ), [])

    for k, v in kwargs.iteritems():
        items.append((k, unicode(v).encode('utf-8')))

    return urlencode(items)
