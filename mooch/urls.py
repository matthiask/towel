import sys
import settings
from django.conf.urls.defaults import *
from django.contrib import admin

from mooch.views import project_view, profile_view

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
    url(r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^accounts/', include('django.contrib.auth.urls')),
    url(r'^projects/', include(project_view.urls)),
    url(r'^profiles/', include(profile_view.urls)),
)

urlpatterns += patterns('django.views.generic.simple',
    #url(r'^$', 'direct_to_template', {'template': 'base.html'}),
    url(r'^$', 'redirect_to', {'url': '/projects/'}),
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



