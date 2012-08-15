from datetime import date, datetime
from decimal import Decimal
import httplib
import json
from lxml.etree import Element, SubElement, tostring

from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse
from django.utils.cache import patch_vary_headers

from towel.api.mimeparse import best_match


class Serializer(object):
    """
    API response serializer

    Handles content type negotiation using the HTTP Accept header if the format
    isn't overridden.
    """
    def serialize(self, data, output_format=None, request=None,
            status=httplib.OK, headers=None):
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
                output_format = best_match(reversed([
                    'application/xml',
                    'application/json',
                    ]),
                    request.META.get('HTTP_ACCEPT'))
            except (IndexError, ValueError):
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

        if headers:
            for key, value in headers.iteritems():
                response[key] = value

        patch_vary_headers(response, ('Accept',))
        response.status_code = status
        return response

    def to_json(self, data):
        return HttpResponse(
            json.dumps(data, cls=DjangoJSONEncoder),
            content_type='application/json',
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
            content_type='application/xml',
            )
