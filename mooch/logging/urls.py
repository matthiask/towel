from django.conf.urls.defaults import *

urlpatterns = patterns('mooch.organisation.views',
    url(r'^new/$', 'entry_new', name='logging_entry_new'),
    url(r'^(?P<object_id>\d+)/$', 'entry_detail', name='logging_entry_detail'),
    url(r'^(?P<object_id>\d+)/edit/$', 'entry_edit', name='logging_entry_edit'),
    url(r'^(?P<object_id>\d+)/delete/$', 'entry_delete', name='logging_entry_delete'),
    url(r'^(?P<object_id>\d+)/add_file$', 'entry_add_file', name='logging_entry_add_file'),
    url(r'^file/delete/(?P<object_id>\d+)/$', 'entry_delete_file', name='logging_entry_delete_file'),
)
