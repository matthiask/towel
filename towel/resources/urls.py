from django.conf.urls import url


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

    def _fn(name, detail, view, suffix=None, mixins=None, decorators=None, **kw):
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
