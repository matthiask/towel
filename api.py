import json

from django.conf.urls import url
from django.db.models import ObjectDoesNotExist
from django.http import Http404, HttpResponse
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
    def as_url(cls, prefix, **initkwargs):
        """
        Usage::

            urlpatterns = patterns('',
                Resource.as_url('v1/product/', model=Product),
            )
        """

        return url(r'^%s(?:(?P<pk>\d+)/)?$' % prefix,
            csrf_exempt(cls.as_view(**initkwargs)))

    def dispatch(self, request, *args, **kwargs):
        # Try to dispatch to the right method; if a method doesn't exist,
        # defer to the error handler. Also defer to the error handler if the
        # request method isn't on the approved list.
        if request.method.lower() in self.http_method_names:
            handler = getattr(self, request.method.lower(), self.http_method_not_allowed)
        else:
            handler = self.http_method_not_allowed
        self.request = request
        self.args = args
        self.kwargs = kwargs
        self.unserialize_request()
        return self.serialize_response(handler(request, *self.args, **self.kwargs))

    def unserialize_request(self):
        """
        This method standardizes various aspects of the incoming request, f.e.
        decoding of JSON requests etc.

        The "real" processing methods should not have to distinguish between
        varying request types anymore.
        """
        pass

    def serialize_response(self, response):
        return HttpResponse(json.dumps(response), mimetype='application/json')

    def get_query_set(self):
        if self.queryset:
            return self.queryset._clone()
        elif self.model:
            return self.model._default_manager.all()

    def serialize_instance(self, instance):
        return {
            'pk': instance.pk,
            '__unicode__': unicode(instance),
            }

    def get(self, request, *args, **kwargs):
        queryset = self.get_query_set()
        if kwargs.get('pk'):
            instance = queryset.get(pk=kwargs.get('pk'))

            return self.serialize_instance(instance)

        # TODO pagination, filtering
        return [self.serialize_instance(instance) for instance in queryset]
