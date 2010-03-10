import sys
import settings
from django.conf.urls.defaults import *
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
    url(r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^accounts/', include('django.contrib.auth.urls')),
    #url(r'^projects/', include('mooch.organisation.urls')),
)

urlpatterns += patterns('django.views.generic.simple',
    #url(r'^$', 'direct_to_template', {'template': 'base.html'}),
    #url(r'^$', 'redirect_to', {'url': '/where/do/you/want/to/go/today/'}),
)

if 'runserver' in sys.argv:
    urlpatterns += patterns('',
        url(r'^media/sys/feincms/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.APP_BASEDIR+'/feincms/media/feincms', 'show_indexes':True}),
        url(r'^media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT, 'show_indexes':True}),
    )

"""
urlpatterns += patterns('',
    url(r'^(.*)$', 'feincms.views.base.handler'),
)
"""


from mooch import generic
from mooch.accounts.utils import Profile, access_level_required
from mooch.organisation.models import Project


def model_view_access_level_required(access_level):
    """
    access_level_required replacement which pops the 'profile' keyword
    argument because the ModelView cannot handle this additional argument
    (yet).
    """

    def dec(fn):
        def _fn(request, *args, **kwargs):
            kwargs.pop('profile')
            return fn(request, *args, **kwargs)
        return access_level_required(access_level)(_fn)
    return dec


project_view = generic.ModelView(Project,
    template_object_name='project',
    view_decorator=model_view_access_level_required(Profile.ADMINISTRATION),
    )

profile_view = generic.ModelView(Profile,
    )

urlpatterns += patterns('',
    url(r'^projects/', include(project_view.urls)),
    url(r'^profiles/', include(profile_view.urls)),
)
