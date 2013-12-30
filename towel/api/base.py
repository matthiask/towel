from __future__ import absolute_import, unicode_literals

from django.core.urlresolvers import NoReverseMatch, reverse
from django.utils.six.moves import http_client

from towel.utils import app_model_label


class APIException(Exception):
    """
    Custom exception which signals a problem detected somewhere inside
    the API machinery.

    Usage::

        # Use official W3C error names from ``httplib.responses``
        raise ClientError(status=httplib.NOT_ACCEPTABLE)

    or::

        raise ServerError('Not implemented, go away',
            status=httplib.NOT_IMPLEMENTED)

    Additional information can be passed through by setting the ``data``
    argument to a dict instance. The :py:exc:`~towel.api.APIException` handler
    will merge the dict into the default error data and return everything
    to the client::

        raise APIException('Validation failed', data={
            'form': form.errors,
            })
    """

    #: The default response is '400 Bad request'
    default_status = http_client.BAD_REQUEST

    def __init__(self, error_message=None, status=None, data={}):
        super(Exception, self).__init__(error_message)

        self.status = self.default_status if status is None else status
        if error_message is None:
            self.error_message = http_client.responses.get(self.status, '')
        else:
            self.error_message = error_message

        self.data = data


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
    try:
        return reverse(
            '_'.join(
                (api_name,) + app_model_label(model) + (ident,)),
            kwargs=kwargs)
    except NoReverseMatch:
        if fail_silently:
            return None
        raise
