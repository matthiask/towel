from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, re_path

from .views import emailaddress_views, message_views, person_views


urlpatterns = [
    re_path(r"^admin/", admin.site.urls),
    re_path(r"^persons/", include(person_views.urls)),
    re_path(r"^emailaddresses/", include(emailaddress_views.urls)),
    re_path(r"^messages/", include(message_views.urls)),
    re_path(r"^resources/", include("testapp.resources")),
] + staticfiles_urlpatterns()
