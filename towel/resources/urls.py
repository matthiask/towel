from __future__ import absolute_import, unicode_literals

from django.conf.urls import url as _url

from towel import resources
from towel.utils import app_model_label

try:
    from django.urls import NoReverseMatch, reverse
except ImportError:
    from django.core.urlresolvers import NoReverseMatch, reverse


class _MRUHelper(object):
    def __init__(self, viewname_pattern, kwargs):
        self.viewname_pattern = viewname_pattern
        self.kwargs = kwargs

    def __getitem__(self, item):
        return self.url(item)

    def url(self, item, *args, **kwargs):
        kw = self.kwargs
        if kwargs:
            kw = kw.copy()
            kw['kwargs'].update(kwargs)

        try:
            return reverse(self.viewname_pattern % item, **kw)
        except NoReverseMatch as e:
            try:
                return reverse(self.viewname_pattern % item)
            except NoReverseMatch:
                # Re-raise exception with kwargs; it's more informative
                raise e


def model_resource_urls(
        reverse_kwargs_fn=lambda object: {'pk': object.pk},
        default='detail'):
    """
    Usage::

        @model_resource_urls()
        class MyModel(models.Model):
            pass

        instance = MyModel.objects.get(...)
        instance.urls.url('detail') == instance.get_absolute_url()
    """
    def _dec(cls):
        class _descriptor(object):
            def __get__(self, obj, objtype=None):
                viewname_pattern = '%s_%s_%%s' % app_model_label(obj)
                kwargs = {'kwargs': reverse_kwargs_fn(obj)}
                helper = obj.__dict__['urls'] = _MRUHelper(
                    viewname_pattern, kwargs)
                return helper

        cls.urls = _descriptor()
        cls.get_absolute_url = lambda self: self.urls.url(default)
        return cls
    return _dec


def resource_url_fn(
        model,
        urlconf_detail_re=r'(?P<pk>\d+)',
        mixins=(),
        decorators=(),
        **kwargs):
    """
    Returns a helper function most useful to easily create URLconf entries
    for model resources.

    The list of decorators should be ordered from the outside to the inside,
    in the same order as you would write them when using the ``@decorator``
    syntax.

    Usage::

        project_url = resource_url_fn(
            Project,
            mixins=(ProjectViewMixin,),
            decorators=(login_required,),
            )
        urlpatterns = [
            project_url('list', url=r'^$', paginate_by=50),
            project_url('detail', url=r'^(?P<pk>\d+)/$'),
            project_url('add', url=r^add/$'),
            project_url('edit'),
            project_url('delete'),
        ]

        # the project URLs will be:
        # ^$
        # ^(?P<pk>\d+)/$
        # ^add/$'
        # ^(?P<pk>\d+)/edit/$
        # ^(?P<pk>\d+)/delete/$

    The returned helper function comes with ``mixins`` and ``decorators``
    arguments too. They default to the values passed into the
    ``resource_url_fn``. If you use those arguments, you have to pass the
    full list of mixins and/or decorators you need. You can pass an empty
    list if some view does not need any mixins and/or decorators.
    """

    global_mixins = mixins
    global_decorators = decorators

    default_view_classes = {
        'list': resources.ListView,
        'detail': resources.DetailView,
        'add': resources.AddView,
        'edit': resources.EditView,
        'delete': resources.DeleteView,
    }

    def _fn(
            name,
            _sentinel=None,
            view=None,
            url=None,
            mixins=None,
            decorators=None,
            **kw):

        if _sentinel is not None:
            raise TypeError('name is the only non-keyword')

        urlregex = (
            r'^%s/%s/$' % (urlconf_detail_re, name)
            if url is None else url
        )

        urlname = '%s_%s_%s' % (app_model_label(model) + (name,))

        mixins = global_mixins if mixins is None else mixins
        decorators = global_decorators if decorators is None else decorators

        kws = kwargs.copy()
        kws.update(kw)

        view = default_view_classes[name] if view is None else view
        view = type(view.__name__, mixins + (view,), {})
        view = view.as_view(model=model, **kws)

        for dec in reversed(decorators):
            view = dec(view)

        return _url(urlregex, view, name=urlname)

    return _fn
