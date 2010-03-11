from datetime import datetime

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

from mooch.organisation.models import Project
from mooch.abstract.models import CreateUpdateModel

LOG_SOURCES = (
    ('WEB', 'Online'),
    ('EML', 'Email'),
    ('SMS', 'SMS'),
    ('MMS', 'MMS'),
)

class LogEntry(CreateUpdateModel):
    account = models.ForeignKey(User, related_name='logentries')
    project = models.ForeignKey(Project, blank=True, null=True,
        related_name="logentries", verbose_name=_('project'))
    title = models.CharField(_('title'), max_length=150)
    message = models.TextField(_('text'))
    source = models.CharField(_('origin'), choices=LOG_SOURCES, max_length=10)
    reported = models.DateTimeField(_('reported'), default=datetime.now)

    class Meta:
        verbose_name = _('log entry')
        verbose_name_plural = _('log entries')
        ordering = ('-reported',)

    def __unicode__(self):
        return self.title

    @models.permalink
    def get_absolute_url(self):
        return ('logging_logentry_detail', (self.pk,), {})
