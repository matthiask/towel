import json

from django.conf.urls import patterns, url
from django.db.models import ObjectDoesNotExist
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import classonlymethod
from django.views import generic
from django.views.decorators.csrf import csrf_exempt


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

    http_method_names = ['get', 'post', 'put', 'delete', 'head', 'patch']

    @classonlymethod
    def urls(cls, **initkwargs):
        """
        Usage::

            urlpatterns = patterns('',
                url(r'^v1/product/', include(api.Resource.urls(model=Product))),
            )
        """

        view = csrf_exempt(cls.as_view(**initkwargs))

        return patterns('',
            url(r'^$', view),
            url(r'^(?P<pk>\d+)/$', view),
            url(r'^(?P<pks>(?:\d+;)*\d+);?/$', view),
        )

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
        Returns a tuple of ``(queryset, list, single)`` denoting the objects
        which should be processed by the request:

        - ``queryset``: Available items, filtered and all (if applicable).
        - ``list``: List of objects or ``None`` if not applicable. Will be used for
          requests such as ``/api/product/1;3/``.
        - ``single``: Single instances if applicable, used for URIs such as
          ``/api/product/1/``.

        Raises a 404 if the referenced items do not exist.
        """
        queryset, list, single = self.get_query_set(), None, None

        # TODO pagination, filtering

        if 'pk' in self.kwargs:
            single = get_object_or_404(queryset, pk=self.kwargs['pk'])
            try:
                single = queryset.get(pk=self.kwargs['pk'])
            except ObjectDoesNotExist:
                raise Http404('Object does not exist.')

        if 'pks' in self.kwargs:
            pks = set(self.kwargs['pks'].split(';'))
            list = queryset.in_bulk(pks).values()

            if len(pks) != len(list):
                raise Http404('Some objects do not exist.')

        return queryset, list, single

    def serialize_instance(self, instance):
        return {
            'pk': instance.pk,
            '__unicode__': unicode(instance),
            }

    def get(self, request, *args, **kwargs):
        queryset, list, single = self.objects()

        if single:
            return self.serialize_instance(single)
        elif list:
            return {
                'objects': [self.serialize_instance(instance) for instance in list],
                }
        else:
            return {
                'objects': [self.serialize_instance(instance) for instance in queryset],
                'meta': {},
                }

    def post(self, request, *args, **kwargs):
        pass
