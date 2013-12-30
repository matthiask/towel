"""
Models for multitenant Django projects
======================================

The models for ``towel.mt`` have to be provided by the project where
``towel.mt`` is used, that's why this file is empty.

The simplest models might look like that::

    from django.contrib.auth.models import User
    from django.db import models


    class Client(models.Model):
        name = models.CharField(max_length=100)


    class Access(models.Model):
        EMPLOYEE = 10
        MANAGEMENT = 20

        ACCESS_CHOICES = (
            (EMPLOYEE, 'employee'),
            (MANAGEMENT, 'management'),
            )

        client = models.ForeignKey(Client)
        user = models.OneToOneField(User)
        access = models.SmallIntegerField(choices=ACCESS_CHOICES)


API methods can be protected as follows::

    from towel.api import API
    from towel.api.decorators import http_basic_auth
    from towel.mt.api import Resource, api_access

    # Require a valid login and an associated Access model:
    api_v1 = API('v1', decorators=[
        csrf_exempt,
        http_basic_auth,
        api_access(Access.EMPLOYEE),
        ])
    api_v1.register(SomeModel,
        view_class=Resource,
        )


Other views::

    from towel.mt import AccessDecorator

    # Do this once somewhere in your project
    access = AccessDecorator()


    @access(Access.MANAGEMENT)
    def management_only_view(request):
        # ...
"""
# Intentionally left empty.

from __future__ import absolute_import, unicode_literals
