"""
Authentication backend which preloads access and client models
==============================================================
"""

from __future__ import absolute_import, unicode_literals

from django.contrib.auth.models import User

from towel.auth import ModelBackend as _ModelBackend
from towel.mt import access_model, client_model


class ModelBackend(_ModelBackend):
    """
    Custom authentication backend for towel-mt

    This authentication backend serves two purposes:

    1. Allowing email addresses as usernames (``authenticate``)
    2. Minimizing DB accesses by fetching additional information about the
       current user earlier (``get_user``)
    """

    def get_user(self, user_id):
        Access = access_model()
        Client = client_model()
        try:
            access = Access.objects.select_related(
                'user',
                Client.__name__.lower(),
            ).get(user=user_id)

            # Ensure reverse accesses do not needlessly query the DB again.
            # Maybe Django already does that for us already... whatever.
            setattr(access.user, User.access.cache_name, access)
            return access.user
        except Access.DoesNotExist:
            pass

        try:
            # Fall back to raw user access
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            pass

        return None
