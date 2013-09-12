from django.core.urlresolvers import NoReverseMatch, reverse
from django.conf.urls import patterns, include, url
from django.db import models
from django.db.models.related import RelatedObject
from django.http import HttpResponse
from django.utils.encoding import force_text
from django.utils.functional import curry
from django.utils.six.moves import http_client
from django.views.decorators.csrf import csrf_exempt

from .serializers import Serializer


class API(object):
    """
    This is the main API object. It does not do much except give an overview
    over all resources. It will hold the necessary bits to have more than one
    API with the same models or resources at the same time (f.e. versions).

    Usage::

        # ... other imports ...
        from functools import partial
        from towel.api import API, serialize_model_instance

        api_v1 = API('v1')

        # Customize serialization: Never include phone numbers and email
        # addresses of customers in API output.
        api_v1.register(
            Customer,
            serializer=partial(serialize_model_instance,
                exclude=('phone', 'email')),
            view_init={
                'queryset': Customer.objects.filter(is_active=True),
                })

        api_v1.register(
            Product,
            view_init={
                'queryset': Product.objects.filter(is_active=True)
                })

        api_v1.register(
            Product,
            canonical=False,
            prefix=r'^library/',
            view_class=LibraryResource,
            view_init={
                'queryset': Product.objects.filter(is_active=True),
                })

        urlpatterns = patterns('',
            url(r'^v1/', include(api_v1.urls)),
        )

    With authentication::

        api_v2 = API('v2', decorators=[csrf_exempt, login_required])

        # register resources as before
    """

    def __init__(self, name, decorators=[csrf_exempt]):
        self.name = name
        self.decorators = decorators

        self.resources = []
        self.serializers = {}
        self.views = []

        self.default_serializer = serialize_model_instance

    @property
    def urls(self):
        """
        Inclusion point in your own URLconf

        Usage::

            from .views import api_v1

            urlpatterns = patterns('',
                url(r'^api/v1/', include(api_v1.urls)),
            )
        """

        def view(request):
            return self.root(request)
        for dec in reversed(self.decorators):
            view = dec(view)

        urlpatterns = [
            url(r'^$', view, name='api_%s' % self.name),
            ]

        for view in self.views:
            urlpatterns.append(url(view['prefix'], view['view']))

        for resource in self.resources:
            urlpatterns.append(url(
                resource['prefix'],
                include(resource['urlpatterns']),
                ))

        return patterns('', *urlpatterns)

    def root(self, request):
        """
        Main API view, returns a list of all available resources
        """
        if request.method == 'OPTIONS':
            response = HttpResponse()
            response['Allow'] = 'GET, HEAD, OPTIONS'
            response['Content-Length'] = 0
            return response

        elif request.method not in ('GET', 'HEAD'):
            return Serializer().serialize({
                'error': 'Not acceptable',
                }, request=request, status=http_client.METHOD_NOT_ALLOWED,
                output_format=request.GET.get('format'))

        response = {
            '__str__': self.name,
            '__uri__': request.build_absolute_uri(
                reverse('api_%s' % self.name)),
            'resources': [],
            }

        for view in self.views:
            response.setdefault('views', []).append({
                '__str__': view['prefix'].strip('^').strip('/'),
                '__uri__': request.build_absolute_uri(u''.join((
                    response['__uri__'],
                    view['prefix'].strip('^')))),
                })

        for resource in self.resources:
            r = {
                '__str__': resource['model'].__name__.lower(),
                '__uri__': request.build_absolute_uri(u''.join((
                    response['__uri__'],
                    resource['prefix'].strip('^')))),
                }

            response['resources'].append(r)
            if resource['canonical']:
                response[resource['model'].__name__.lower()] = r

        return Serializer().serialize(response, request=request,
            output_format=request.GET.get('format'))

    def register(self, model, view_class=None, canonical=True,
            decorators=None, prefix=None, view_init=None,
            serializer=None):
        """
        Registers another resource on this API. The sole required argument is
        the Django model which should be exposed. The other arguments are:

        - ``view_class``: The resource view class used, defaults to
          :class:`towel.api.Resource`.
        - ``canonical``: Whether this resource is the canonical location of
          the model in this API. Allows registering the same model several
          times in the API (only one location should be the canonical
          location!)
        - ``decorators``: A list of decorators which should be applied to the
          view. Function decorators only, method decorators aren't supported.
          The list is applied in reverse, the order is therefore the same as
          with the ``@`` notation. If unset, the set of decorators is
          determined from the API initialization. Pass an empty list if you
          want no decorators at all. Otherwise API POSTing will have to
          include a valid CSRF middleware token.
        - ``prefix``: The prefix for this model, defaults to the model name in
          lowercase. You should include a caret and a trailing slash if you
          specify this yourself (``prefix=r'^library/'``).
        - ``view_init``: Python dictionary which contains keyword arguments
          used during the instantiation of the ``view_class``.
        - ``serializer``: Function which takes a model instance, the API
          instance and additional keyword arguments (accept ``**kwargs`` for
          forward compatibility) and returns the serialized representation as
          a Python dict.
        """

        from .resources import Resource  # XXX :-(

        view_class = view_class or Resource
        view_init = view_init or {}

        if 'model' not in view_init:
            if 'queryset' in view_init:
                view_init['model'] = view_init['queryset'].model
            else:
                view_init['model'] = model

        view = view_class.as_view(api=self, **view_init)

        name = lambda ident: None
        if canonical:
            opts = model._meta
            name = lambda ident: '_'.join((
                self.name, opts.app_label, opts.module_name, ident))

        if decorators is None:
            decorators = self.decorators

        if decorators:
            for dec in reversed(decorators):
                view = dec(view)

        self.resources.append({
            'model': model,
            'canonical': canonical,
            'prefix': prefix or r'^%s/' % model.__name__.lower(),
            'urlpatterns': patterns('', *[
                url(regex, view, data, name=name(suffix))
                for regex, suffix, data in view_class.urls
                ]),
            })

        if serializer:
            self.serializers[model] = serializer

    def set_default_serializer(self, serializer):
        """
        By default, ``serialize_model_instance`` is used to serialize models.
        This can be changed by passing a different function to this method.
        """
        self.default_serializer = serializer

    def serialize_instance(self, instance, **kwargs):
        """
        Returns a serialized version of the passed model instance

        This method should always be used for serialization, because it knows
        about custom serializers specified when registering resources with
        this API.
        """
        serializer = self.serializers.get(instance.__class__,
            self.default_serializer)
        return serializer(instance, api=self, **kwargs)

    def add_view(self, view, prefix=None, decorators=None):
        """
        Add custom views to this API

        The prefix is automatically determined if not given based on the
        function name.

        The view receives an additional keyword argument ``api`` containing
        the API instance.
        """

        prefix = prefix or r'^%s/' % view.__name__

        if decorators is None:
            decorators = self.decorators

        view = curry(view, api=self)
        for dec in reversed(decorators):
            view = dec(view)

        self.views.append({
            'prefix': prefix,
            'view': view,
            })


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
    opts = model._meta
    try:
        return reverse(
            '_'.join((api_name, opts.app_label, opts.module_name, ident)),
            kwargs=kwargs)
    except NoReverseMatch:
        if fail_silently:
            return None
        raise


def serialize_model_instance(instance, api, inline_depth=0,
        fields=(), exclude=(),
        only_registered=True, build_absolute_uri=lambda uri: uri,
        **kwargs):
    """
    Serializes a single model instance.

    If ``inline_depth`` is a positive number, ``inline_depth`` levels of
    related objects are inlined. The performance implications of this feature
    might be severe! Note: Additional arguments specified when calling
    ``serialize_model_instance`` such as ``exclude``, ``only_registered`` and
    further keyword arguments are currently **not** forwarded to inlined
    objects. Those parameters should be set upon resource registration time as
    documented in the ``API`` docstring above.

    The ``fields`` and ``exclude`` parameters are especially helpful when used
    together with ``functools.partial``.

    Set ``only_registered=False`` if you want to serialize models which do not
    have a canonical URI inside this API.

    ``build_absolute_uri`` should be a callable which transforms any passed
    URI fragment into an absolute URI including the protocol and the hostname,
    for example ``request.build_absolute_uri``.

    This implementation has a few characteristics you should be aware of:

    - Only objects which have a canonical URI inside this particular API are
      serialized; if no such URI exists, this method returns ``None``. This
      behavior can be overridden by passing ``only_registered=False``.
    - Many to many relations are only processed if ``inline_depth`` has a
      positive value. The reason for this design decision is that the database
      has to be queried for showing the URIs of related objects anyway and
      because of that we either show the full objects or nothing at all.
    - Some fields (currently only fields with choices) have a machine readable
      and a prettified value. The prettified values are delivered inside the
      ``__pretty__`` dictionary for your convenience.
    - The primary key of the model instance is always available as
      ``__pk__``.
    """

    # It's not exactly a fatal error, but it helps during development. This
    # statement will disappear in the future.
    assert not kwargs, 'Unknown keyword arguments to serialize_model_instance'

    uri = api_reverse(instance, 'detail', api_name=api.name,
        pk=instance.pk, fail_silently=True)

    if uri is None and only_registered:
        return None

    data = {
        '__uri__': build_absolute_uri(uri),
        '__str__': force_text(instance),
        '__pretty__': {},
        '__pk__': instance.pk,
        }
    opts = instance._meta

    for f_name in opts.get_all_field_names():
        f, model, direct, m2m = opts.get_field_by_name(f_name)

        if fields and f.name not in fields:
            continue

        if f.name in exclude:
            continue

        # TODO maybe check before querying the database whether the objects
        # are included in the API or only_registered=False?

        if isinstance(f, (models.ManyToManyField, RelatedObject)):
            if inline_depth > 0:
                is_relobj = isinstance(f, RelatedObject)
                name = f.get_accessor_name() if is_relobj else f.name

                if is_relobj and not f.field.rel.multiple:
                    try:
                        obj = getattr(instance, name)
                    except models.ObjectDoesNotExist:
                        obj = None

                    data[name] = api.serialize_instance(
                        obj,
                        inline_depth=inline_depth - 1,
                        build_absolute_uri=build_absolute_uri,
                        only_registered=only_registered,
                        ) if obj else None
                else:
                    related = [api.serialize_instance(
                        obj,
                        inline_depth=inline_depth - 1,
                        build_absolute_uri=build_absolute_uri,
                        only_registered=only_registered,
                        ) for obj in getattr(instance, name).all()]
                    if any(related):
                        data[name] = related

        elif f.rel:
            value = f.value_from_object(instance)
            if value is None:
                data[f.name] = None
                continue

            try:
                data[f.name] = build_absolute_uri(api_reverse(
                    f.rel.to,
                    'detail',
                    api_name=api.name,
                    pk=f.value_from_object(instance)))
            except NoReverseMatch:
                if only_registered:
                    continue

            if inline_depth > 0:
                related = getattr(instance, f.name)

                if related:
                    # XXX What about only_registered, kwargs? Should they be
                    # passed to other calls as well, or should we assume that
                    # customization can only happen using functools.partial
                    # upon registration time?
                    data[f.name] = api.serialize_instance(
                        related,
                        inline_depth=inline_depth - 1,
                        build_absolute_uri=build_absolute_uri,
                        only_registered=only_registered,
                        )

        elif isinstance(f, models.FileField):
            # XXX add additional informations to the seralization?
            try:
                value = f.value_from_object(instance)
                data[f.name] = build_absolute_uri(value.url)
            except ValueError:
                data[f.name] = ''

        else:
            data[f.name] = f.value_from_object(instance)

            if f.flatchoices:
                data['__pretty__'][f.name] = force_text(
                    dict(f.flatchoices).get(data[f.name], '-'))

    return data
