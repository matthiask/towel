import json
import re

from django.utils.six.moves import http_client

from .serializers import Serializer


class RequestParser(object):
    """
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
    """
    def parse(self, request):
        """
        Decides whether the request body should be parsed, and if yes, decides
        which parser to use. Returns a HTTP 415 Unsupported media type if the
        request isn't understood.
        """
        if request.method in ('GET', 'HEAD', 'OPTIONS', 'TRACE', 'DELETE'):
            # Fall back to standard handling which only does stuff when
            # method == 'POST' anyway, that is, not now.
            return

        content_type = request.META.get('CONTENT_TYPE',
            'application/x-www-form-urlencoded')

        handlers = {
            r'^application/x-www-form-urlencoded': self.parse_form,
            r'^multipart/form-data': self.parse_form,
            r'^application/json': self.parse_json,
        }

        for pattern, handler in handlers.items():
            if re.match(pattern, content_type):
                return handler(request)

        return Serializer().serialize({
            'error': '%r is not supported' % content_type,
            }, request=request, status=http_client.UNSUPPORTED_MEDIA_TYPE,
            output_format=request.GET.get('format'))

    def parse_form(self, request):
        """
        Simply calls Django's own request parsing, but changes the request
        method to ``'POST'`` so that the request body parsing actually happens
        as it should. The value of ``request.method`` is restored when
        parsing ends.
        """
        method = request.method
        request.method = 'POST'
        request._load_post_and_files()
        request.method = method

    def parse_json(self, request):
        """
        Unserializes the JSON in the body of the request and saves the result
        as ``request.POST``.
        """
        request.POST = json.loads(request.body.decode('utf-8'))
