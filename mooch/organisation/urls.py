from django.conf.urls.defaults import *

urlpatterns = patterns('mooch.organisation.views',
    url(r'^list/$', 'project_list', name='organisation_project_list'),
    url(r'^new/$', 'project_new', name='organisation_project_new'),
    url(r'^(?P<object_id>\d+)/$', 'project_detail', name='organisation_project_detail'),
    url(r'^(?P<object_id>\d+)/edit/$', 'project_edit', name='organisation_project_edit'),
    url(r'^(?P<object_id>\d+)/delete/$', 'project_delete', name='organisation_project_delete'),
    url(r'^(?P<object_id>\d+)/add_file$', 'project_add_file', name='organisation_project_add_file'),
    url(r'^file/delete/(?P<object_id>\d+)/$', 'project_delete_file', name='organisation_project_delete_file'),
)

urlpatterns += patterns('django.views.generic.simple',
    url(r'^$', 'redirect_to', {'url': 'list/'}),

)
