from collections import namedtuple
import json
from urllib import urlencode

from django.conf.urls import patterns, include, url
from django.core import paginator
from django.core.serializers.json import DjangoJSONEncoder
from django.core.urlresolvers import NoReverseMatch, reverse
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import classonlymethod
from django.views import generic
from django.views.decorators.csrf import csrf_exempt


Objects = namedtuple('Objects', 'queryset page set single')


class API(object):
    """
    This is the main API object. It does not do much except give an overview over
    all resources. It will hold the necessary bits to have more than one API
    with the same models or resources at the same time (f.e. versions).

    Usage::

        api_v1 = API('v1')
        api_v1.register(Customer, Resource.urls(model=Customer, api_name='v1'))
        api_v1.register(Store, Resource.urls(model=Store, api_name='v1'))
        api_v1.register(Product, Resource.urls(model=Product, api_name='v1'))

        urlpatterns = patterns('',
            url(r'^v1/', include(api_v1.urls)),
        )
    """

    def __init__(self, name):
        self.name = name
        self.resources = []

    def register(self, model, urls, prefix=None):
        """
        Registers another resource on this API. The first argument is the Django
        model exposed through the URL patterns passed as the second argument. The
        third argument can be optionally used to override the URL prefix for the
        given model. The default is to lowercase the model name.o

        Usage::

            api_v1.register(Product, Resource.urls(model=Product, api_name='v1'))

            # Use 'customers' instead of 'customer'
            api_v1.register(Customer, Resource.urls(model=Customer, api_name='v1'),
                r'^customers/')
        """
        self.resources.append((model, urls, prefix or r'^%s/' % model.__name__.lower()))

    @property
    def urls(self):
        """
        Inclusion point in your own URLconf

        Pass the return value to ``include()``.
        """
        urlpatterns = [
            url(r'^$', self, name='api_%s' % self.name),
            ]

        for model, urls, prefix in self.resources:
            urlpatterns.append(url(prefix, include(urls)))

        return patterns('', *urlpatterns)

    def __call__(self, request):
        """
        Main API view, returns a list of all available resources
        """
        response = {
            'name': self.name,
            '__uri__': reverse('api_%s' % self.name),
            }
        for model, urls, prefix in self.resources:
            response[model.__name__.lower()] = {
                '__uri__': api_reverse(model, 'list', api_name=self.name),
                }

        # TODO content negotiation :-(
        return HttpResponse(json.dumps(response), mimetype='application/json')


def api_reverse(model, ident, api_name='api', **kwargs):
    """
    Determines the URL of API endpoints for arbitrary models

    ``model`` is the Django model you want to use, ident should be one of
    ``list``, ``set`` or ``detail`` at the moment, additional keyword arguments
    are forwarded to the ``django.core.urlresolvers.reverse`` call.

    Usage::

        api_reverse(Product, 'detail', pk=42)

    Passing an instance works too::

        api_reverse(instance, 'detail', pk=instance.pk)
    """
    opts = model._meta
    return reverse('_'.join((api_name, opts.app_label, opts.module_name, ident)),
        kwargs=kwargs)


class Resource(generic.View):
    """
    Request-response cycle
    ======================

    - Incoming request with a certain HTTP verb
      - Standardize incoming data (PUTted JSON, POSTed multipart, whatever)

    - Process verbs
      - GET & HEAD
        - list
        - detail
      - POST
        - process
        - create
      - PUT (Complete resource)
        - replace or create
      - PATCH
        - patch, incomplete resources allowed
      - DELETE
        - obvious :-)
      - OPTIONS (unsupported)
      - TRACE (unsupported)
    """

    api_name = None
    model = None
    queryset = None
    paginate_by = 20

    http_method_names = ['get', 'post', 'put', 'delete', 'head', 'patch']

    @classonlymethod
    def urls(cls, canonical=True, api_name='api', decorators=None, **initkwargs):
        """
        Instantiates the view and adds URL entries for the list, set and detail flavors

        This method requires either ``model`` or ``queryset`` as keyword argument.

        If ``canonical`` is ``True``, names are added to the URL patterns for ``reverse()``
        support. ``api_name`` defines the prefix used. If you specify anything, be sure to
        pass this value to ``api_reverse()`` calls too.

        ``decorators`` may be used to decorate the view. The decorators will be applied
        in reverse, the order is therefore the same as with the ``@`` notation.  Only use
        function decorators, NOT method decorators here.

        All other keyword arguments are forwarded to ``Resource.as_view()``. This
        method requires either a ``model`` or a ``queryset`` keyword argument.

        Usage::

            urlpatterns = patterns('',
                url(r'^v1/product/', include(api.Resource.urls(model=Product))),
            )
        """

        model = initkwargs.get('model') or initkwargs.get('queryset').model
        initkwargs.setdefault('model', model)

        view = csrf_exempt(cls.as_view(api_name=api_name, **initkwargs))

        name = lambda ident: None
        if canonical:
            opts = model._meta
            name = lambda ident: '_'.join((
                api_name, opts.app_label, opts.module_name, ident))

        if decorators:
            for dec in reversed(decorators):
                view = dec(view)

        return patterns('',
            url(r'^$', view, name=name('list')),
            url(r'^(?P<pk>\d+)/$', view, name=name('detail')),
            url(r'^(?P<pks>(?:\d+;)*\d+);?/$', view, name=name('set')),
        )

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

        return self.serialize_response(handler(
            self.request, *self.args, **self.kwargs))

    def unserialize_request(self):
        """
        This method standardizes various aspects of the incoming request, f.e.
        decoding of JSON requests etc.

        The "real" processing methods should not have to distinguish between
        varying request types anymore.
        """
        pass

    def serialize_response(self, response):
        """
        Serializes the response into an appropriate format for the wire such as
        JSON. ``HttpResponse`` instances are returned directly.
        """
        if isinstance(response, HttpResponse):
            return response

        # TODO content type negotiation :-)
        # Steal code here:
        # https://github.com/toastdriven/django-tastypie/blob/master/tastypie/utils/mime.py
        # Should also patch the Vary: header to include the Accept: header
        # too, because otherwise cache control is not working as it should
        # patch_vary_headers(response, ('Accept',))
        return HttpResponse(
            json.dumps(response, cls=DjangoJSONEncoder),
            mimetype='application/json')

    def get_query_set(self):
        """
        Returns the queryset used by this resource. If you need access or visibility control,
        add it here.
        """
        if self.queryset:
            return self.queryset._clone()
        elif self.model:
            return self.model._default_manager.all()

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
            # TODO apply filters / searches

            p = paginator.Paginator(queryset, self.paginate_by)

            try:
                page = p.page(self.request.GET.get('page'))
            except paginator.PageNotAnInteger:
                page = p.page(1)
            except EmptyPage:
                page = p.page(p.num_pages)

        return Objects(queryset, page, set_, single)

    def serialize_instance(self, instance):
        """
        Serializes a single model instance.
        """
        opts = instance._meta
        data = {
            '__uri__': api_reverse(self.model, 'detail', api_name=self.api_name,
                pk=instance.pk),
            '__unicode__': unicode(instance),
            }

        for f in opts.fields: # Leave out opts.many_to_many
            if f.rel:
                try:
                    data[f.name] = api_reverse(f.rel.to, 'detail', api_name=self.api_name,
                        pk=f.value_from_object(instance))
                except NoReverseMatch:
                    continue

            else:
                data[f.name] = f.value_from_object(instance)

        return data

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
            return self.serialize_instance(objects.single)
        elif objects.set:
            return {
                'objects': [self.serialize_instance(instance) for instance in objects.set],
                }
        else:
            page = objects.page
            list_url = api_reverse(self.model, 'list', api_name=self.api_name)
            meta = {
                'pages': page.paginator.num_pages,
                'count': page.paginator.count,
                'current': page.number,
                }
            if page.number > 1:
                meta['previous'] = u'%s?%s' % (list_url, urlencode({
                    'page': page.number - 1,
                    }))
            if page.number < page.paginator.num_pages:
                meta['next'] = u'%s?%s' % (list_url, urlencode({
                    'page': page.number + 1,
                    }))

            return {
                'objects': [self.serialize_instance(instance) for instance in page],
                'meta': meta,
                }
