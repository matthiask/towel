from datetime import date, timedelta
from decimal import Decimal
import random
import re
import string

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q, Sum
from django.utils.translation import ugettext_lazy as _

from mooch.abstract.models import CreateUpdateModel
from mooch.organisation.models import NGO


def generate_apikey():
    return u''.join([random.choice(string.letters+string.digits) for i in range(40)])


class Profile(CreateUpdateModel):
    DONATOR = 10
    REPORTER = 20
    ADMINISTRATION = 30

    LEVEL_CHOICES = (
        (ADMINISTRATION, _('Administration')),
        #(PROJECTMANAGER, _('Project Manager')), # not implemented in prototype
        (REPORTER, _('Field Reporter')),
        (DONATOR, _('Donator')),
        )

    user = models.ForeignKey(User, unique=True, verbose_name=_('Worker'))

    ngo = models.ForeignKey(NGO, related_name='profiles')
    #person = models.ForeignKey(Person, unique=True, verbose_name=_('Person'))

    notes = models.TextField(_('Notes'), blank=True)

    access_level = models.IntegerField(_('Access level'), choices=LEVEL_CHOICES)

    apikey = models.CharField(_('API Key'), max_length=40, unique=True,
        default=generate_apikey)

    language = models.CharField(_('Language'), max_length=10, blank=True)

    def __unicode__(self):
        return u'Profile for %s' % self.user

    def regenerate_apikey(self):
        self.apikey = generate_apikey()

    @models.permalink
    def get_absolute_url(self):
        return ('accounts_profile_detail', (self.user.username,), {})

    @property
    def is_administration(self):
        return self.access_level>=self.ADMINISTRATION

