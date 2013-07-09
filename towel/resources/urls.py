from django.conf.urls import url
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
        default='detail',
        ):
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
                viewname_pattern = '%s_%s_%%s' % (
                    obj._meta.app_label,
                    obj._meta.module_name,
                    )
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
        urlconf_detail_re=r'(?P<pk>\d+)/',
        mixins=(),
        decorators=(),
        **kwargs
        ):
    """
    Returns a helper function most useful to easily create URLconf entries
    for model resources.

    The list of decorators should be ordered from the outside to the inside,
    in the same order as you would write them when using the ``@decorator``
    syntax.

    Usage::

        project_url = resource_url_fn(Project,
            mixins=(ProjectViewMixin,),
            decorators=(login_required,),
            )
        urlpatterns = patterns('',
            # list and detail  both have suffix='' added so that their URLs
            # do not end with /list/ and /detail/ respectively.
            project_url('list', False, ListView, suffix=''),
            project_url('detail', True, DetailView, suffix=''),
            project_url('add', False, AddView),
            project_url('edit', True, EditView),
            project_url('delete', True, EditView),
        )

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

    def _fn(name, detail, view, suffix=None, mixins=None, decorators=None,
            **kw):
        urlregex = r'^%s%s$' % (
            urlconf_detail_re if detail else r'',
            name + '/' if suffix is None else suffix,
            )

        urlname = '%s_%s_%s' % (
            model._meta.app_label,
            model._meta.module_name,
            name,
            )

        mixins = global_mixins if mixins is None else mixins
        decorators = global_decorators if decorators is None else decorators

        kws = kwargs.copy()
        kws.update(kw)

        view = type(view.__name__, mixins + (view,), {})
        view = view.as_view(model=model, **kws)

        for dec in reversed(decorators):
            view = dec(view)

        return url(urlregex, view, name=urlname)
    return _fn
