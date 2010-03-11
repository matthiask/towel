from django.conf.urls.defaults import *

urlpatterns = patterns('mooch.mobile.views',
    url(r'^test/$', 'test_view', name='mobile_test'),
    url(r'^donations/$','receive_donation', name='mobile_recieve_donation'),
    url(r'^reports/$','receive_report', name='mobile_recieve_report'),
)
