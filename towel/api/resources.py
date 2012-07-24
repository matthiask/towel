from collections import namedtuple
import httplib

from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.views import generic

from .api import APIException, api_reverse
from .parsers import RequestParser
from .serializers import Serializer
from .utils import querystring


#: The return value of ``Resource.objects``
Objects = namedtuple('Objects', 'queryset page set single')


#: The ``page`` object from ``Resource.objects``
Page = namedtuple('Page', 'queryset offset limit total')


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

        response = self.unserialize_request()
        if response:
            return response

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
        except Http404 as exc:
            return self.serialize_response({'error': exc[0]},
                status=httplib.NOT_FOUND)
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

    def serialize_response(self, response, status=httplib.OK, headers=None):
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
