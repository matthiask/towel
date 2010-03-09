from datetime import datetime

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

from mooch.accounts.models import Profile
from mooch.accounts.middleware import get_current_user, get_current_profile
from mooch.abstract.models import BaseModel, CreateUpdateModel

LOG_SOURCES = (
    ('WEB', 'Online'),
    ('EML', 'Email'),
    ('SMS', 'SMS'),
    ('MMS', 'MMS'),
)

class LogEntry(CreateUpdateModel):
    account = models.ForeignKey(Profile, default=get_current_profile)
    title = models.CharField(_('title'), max_length=150)
    message = models.TextField(_('text'))
    source = models.CharField(_('origin'), choices=LOG_SOURCES, max_length=10)
    reported = models.DateTimeField(_('reported'), default=datetime.now)
    
    class Meta:
        verbose_name = _('Log Entry')
        verbose_name_plural = _('Log Entries')
        ordering = ('-reported',)

