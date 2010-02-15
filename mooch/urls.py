from django.conf.urls.defaults import *
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
    url(r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^accounts/', include('django.contrib.auth.urls')),
)

urlpatterns += patterns('django.views.generic.simple',
    url(r'^$', 'direct_to_template', {'template': 'base.html'}),
    #url(r'^$', 'redirect_to', {'url': '/where/do/you/want/to/go/today/'}),
)

urlpatterns += patterns('',
    #url(r'^(.*)$', 'feincms.views.base.handler'),
)

"""
if settings.LOCAL_DEV:
    urlpatterns += patterns('',
        url(r'^media/(?P<path>.*)$', 'django.views.static.serve',
            {'document_root': settings.MEDIA_ROOT}),
    )
"""
