from collections import namedtuple
import json
from urllib import urlencode

from django.conf.urls import patterns, include, url
from django.core import paginator
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import classonlymethod
from django.views import generic
from django.views.decorators.csrf import csrf_exempt


Objects = namedtuple('Objects', 'queryset page set single')


class API(object):
    def __init__(self, name):
        self.name = name
        self.resources = []

    def register(self, model, urls, prefix=None):
        self.resources.append((model, urls, prefix or r'^%s/' % model.__name__.lower()))

    @property
    def urls(self):
        urlpatterns = [
            url(r'^$', self),
            ]

        for model, urls, prefix in self.resources:
            urlpatterns.append(url(prefix, include(urls)))

        return patterns('', *urlpatterns)

    def __call__(self, request):
        # TODO remove hardcoded shit :-(

        response = {
            'name': self.name,
            '__uri__': request.path,
            }
        for model, urls, prefix in self.resources:
            opts = model._meta
            response[model.__name__.lower()] = {
                '__uri__': reverse('api_%s_%s_list' % (
                    opts.app_label, opts.module_name)),
                }

        return HttpResponse(json.dumps(response), mimetype='application/json')


def api_reverse(model, ident, **kwargs):
    opts = model._meta
    return reverse('api_%s_%s_%s' % (opts.app_label, opts.module_name, ident),
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
    model = None
    queryset = None
    paginate_by = 20

    http_method_names = ['get', 'post', 'put', 'delete', 'head', 'patch']

    @classonlymethod
    def urls(cls, canonical=True, **initkwargs):
        """
        Usage::

            urlpatterns = patterns('',
                url(r'^v1/product/', include(api.Resource.urls(model=Product))),
            )
        """

        model = initkwargs.get('model') or initkwargs.get('queryset').model
        initkwargs.setdefault('model', model)

        view = csrf_exempt(cls.as_view(**initkwargs))

        name = lambda ident: None
        if canonical:
            opts = model._meta
            name = lambda ident: 'api_%s_%s_%s' % (
                opts.app_label,
                opts.module_name,
                ident,
                )

        return patterns('',
            url(r'^$', view, name=name('list')),
            url(r'^(?P<pk>\d+)/$', view, name=name('detail')),
            url(r'^(?P<pks>(?:\d+;)*\d+);?/$', view, name=name('set')),
        )

    def reverse(self, ident, **kwargs):
        return api_reverse(self.model, ident, **kwargs)

    def dispatch(self, request, *args, **kwargs):
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
        if isinstance(response, HttpResponse):
            return response

        # TODO content type negotiation :-)
        # Steal code here:
        # https://github.com/toastdriven/django-tastypie/blob/master/tastypie/utils/mime.py
        # Should also patch the Vary: header to include the Accept: header
        # too, because otherwise cache control is not working as it should
        # patch_vary_headers(response, ('Accept',))
        return HttpResponse(json.dumps(response), mimetype='application/json')

    def get_query_set(self):
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
        return {
            '__unicode__': unicode(instance),
            '__uri__': self.reverse('detail', pk=instance.pk),
            }

    def get(self, request, *args, **kwargs):
        objects = self.objects()

        if objects.single:
            return self.serialize_instance(objects.single)
        elif objects.set:
            return {
                'objects': [self.serialize_instance(instance) for instance in objects.set],
                }
        else:
            page = objects.page
            list_url = self.reverse('list')
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
