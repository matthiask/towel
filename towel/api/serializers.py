import json

from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse
from django.utils.cache import patch_vary_headers
from django.utils.six.moves import http_client

from towel.api.mimeparse import best_match


class Serializer(object):
    """
    API response serializer

    Handles content type negotiation using the HTTP Accept header if the
    format isn't overridden.
    """
    def serialize(self, data, output_format=None, request=None,
            status=http_client.OK, headers=None):
        """
        Returns a ``HttpResponse`` containing the serialized response in the
        format specified explicitly in ``output_format`` (either as a MIME
        type or as a simple identifier) or according to the HTTP Accept
        header specified in the passed request instance. The default status
        code is ``200 OK``, if that does not fit you'll have to specify a
        different code yourself.

        Returns a ``406 Not acceptable`` response if the requested format is
        unknown or unsupported. Currently, the following formats are
        supported:

        - ``json`` or ``application/json``

        Usage::

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
                output_format = best_match(reversed([
                    'application/json',
                    ]),
                    request.META.get('HTTP_ACCEPT', ''))
            except (IndexError, ValueError):
                pass

        if output_format in ('application/json', 'json'):
            response = self.to_json(data)

        else:
            # Cannot raise ClientError here because the APIException handler
            # calls into this method too.
            response = HttpResponse('Not acceptable')
            status = http_client.NOT_ACCEPTABLE

        if headers:
            for key, value in headers.items():
                response[key] = value

        patch_vary_headers(response, ('Accept',))
        response.status_code = status
        return response

    def to_json(self, data):
        return HttpResponse(
            json.dumps(data, cls=DjangoJSONEncoder),
            content_type='application/json',
            )
