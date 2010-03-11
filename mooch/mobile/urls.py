from django.conf.urls.defaults import *

urlpatterns = patterns('mooch.mobile.views',
    url(r'^test/$', 'test_view', name='mobile_test'),
)
