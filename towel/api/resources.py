from collections import namedtuple

from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.six.moves import http_client
from django.views import generic

from .api import APIException, api_reverse
from .parsers import RequestParser
from .serializers import Serializer
from .utils import querystring


#: The ``page`` object from ``Resource.objects``
Page = namedtuple('Page', 'queryset offset limit full_queryset')


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

    #: A list of URL patterns which will be used by ``API.register`` to build
    #: the URLconf entries. The format is a list of tuples containing
    #: (regular expression, URL name suffix).
    urls = [
        (r'^$', 'list', {
            'request_type': 'list',
            }),
        (r'^(?P<pk>\d+)/$', 'detail', {
            'request_type': 'detail',
            }),
        (r'^(?P<pks>(?:\d+;)*\d+);?/$', 'set', {
            'request_type': 'set',
            }),
        ]

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

        # The following three lines can be removed when we move to
        # Django 1.5 only
        self.request = request
        self.args = args
        self.kwargs = kwargs

        response = self.unserialize_request()
        if response:
            return response

        # Try to dispatch to the right method; if a method doesn't exist,
        # defer to the error handler. Also defer to the error handler if the
        # request method isn't on the approved list.
        method = self.request.method.lower()
        if method == 'head':
            method = 'get'
        handler = self.http_method_not_allowed

        if method in self.http_method_names:
            self.request_type = kwargs.get('request_type')
            if (self.request_type
                    and hasattr(self, '%s_%s' % (method, self.request_type))):
                handler = getattr(self, '%s_%s' % (method, self.request_type))
            elif hasattr(self, method):
                handler = getattr(self, method)

        try:
            return self.serialize_response(
                handler(self.request, *self.args, **self.kwargs))
        except Http404 as exc:
            return self.serialize_response({'error': exc.args[0]},
                status=http_client.NOT_FOUND)
        except APIException as exc:
            data = {
                'error': exc.error_message,
                }
            data.update(exc.data)
            return self.serialize_response(data, status=exc.status)

    def unserialize_request(self):
        """
        This method standardizes various aspects of the incoming request, f.e.
        decoding of JSON requests etc.

        The "real" processing methods should not have to distinguish between
        varying request types anymore.

        If this method returns anything, it is treated as a response and
        short-circuits the resource processing.
        """
        return RequestParser().parse(self.request)

    def serialize_response(self, response,
            status=http_client.OK, headers=None):
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

    def detail_object_or_404(self):
        """
        Returns the current object for detail resources such as
        ``/api/product/1/``.
        """
        return get_object_or_404(self.get_query_set(), pk=self.kwargs['pk'])

    def set_objects_or_404(self):
        """
        Returns the current set of objects for set resources such as
        ``/api/product/1;3/``.
        """
        pks = set(pk for pk in self.kwargs['pks'].split(';') if pk)
        set_ = self.get_query_set().in_bulk(pks).values()

        if len(pks) != len(set_):
            raise Http404('Some objects do not exist.')

        return set_

    def page_objects_or_404(self):
        """
        Returns the current page for list resources such as
        ``/api/product/?limit=20&offset=40``. Applies filtering using
        ``apply_filters`` as well.
        """
        queryset = self.apply_filters(self.get_query_set())

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

        return Page(queryset[offset:offset + limit], offset, limit, queryset)

    def get_detail(self, request, *args, **kwargs):
        kw = {}
        if request.GET.get('full'):
            kw['inline_depth'] = 1
        return self.api.serialize_instance(
            self.detail_object_or_404(),
            build_absolute_uri=request.build_absolute_uri,
            **kw)

    def get_set(self, request, *args, **kwargs):
        return {
            'objects': [
                self.api.serialize_instance(
                    instance,
                    build_absolute_uri=request.build_absolute_uri,
                    ) for instance in self.set_objects_or_404()],
            }

    def get_list(self, request, *args, **kwargs):
        page = self.page_objects_or_404()

        list_url = api_reverse(page.full_queryset.model, 'list',
            api_name=self.api.name)
        meta = {
            'offset': page.offset,
            'limit': page.limit,
            'total': page.full_queryset.count(),
            'previous': None,
            'next': None,
            }

        if page.offset > 0:
            meta['previous'] = request.build_absolute_uri(
                u'%s?%s' % (list_url, querystring(
                    self.request.GET,
                    exclude=('offset', 'limit'),
                    offset=max(0, page.offset - page.limit),
                    limit=page.limit,
                    )))

        if page.offset + page.limit < meta['total']:
            meta['next'] = request.build_absolute_uri(
                u'%s?%s' % (list_url, querystring(
                    self.request.GET,
                    exclude=('offset', 'limit'),
                    offset=page.offset + page.limit,
                    limit=page.limit,
                    )))

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
        methods = set(m.upper() for m in self.http_method_names if (
            hasattr(self, m)
            or hasattr(self, '%s_%s' % (m, self.request_type))
            ))
        if 'GET' in methods:
            methods.add('HEAD')
        return sorted(methods)
