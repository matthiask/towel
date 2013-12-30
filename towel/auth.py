from __future__ import absolute_import, unicode_literals

from django.contrib.auth.backends import ModelBackend as _ModelBackend
from django.contrib.auth.models import User


class ModelBackend(_ModelBackend):
    """
    Add the following to your ``settings.py`` to be able to login with
    email addresses too::

        AUTHENTICATION_BACKENDS = (
            'towel.auth.ModelBackend',
        )
    """
    def authenticate(self, username=None, password=None):
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            try:
                user = User.objects.get(email=username)
            except User.DoesNotExist:
                return None

        if user.check_password(password):
            return user

        return None
