from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from countries.models import Country

from mooch.accounts.middleware import get_current_user
from mooch.abstract.models import BaseModel, CreateUpdateModel

class NGO(BaseModel):
    full_name = models.CharField(_('elaborate name'), max_length=100)
    logo = models.ImageField(_('logo'), upload_to='img/upload/logos')
    homepage = models.URLField(_('homepage'), verify_exists=False)

    # maybe we need some kind of overall contact person?

    # payment account?

    class Meta:
        verbose_name = _('organisation')
        verbose_name_plural = _('organisations')


def get_current_ngo():
    try:
        return get_current_user().get_profile().ngo
    except:
        return None


class Project(CreateUpdateModel):
    STATES = (
        ('PLANNING', _('In planning')),
        ('FUNDRAISING', _('Fund raising')),
        ('REALISATION', _('In realisation')),
        ('FINISHED', _('Finished')),
    )

    name = models.CharField(_('name'), max_length=100)
    ngo = models.ForeignKey(NGO, default=get_current_ngo,
        verbose_name=_('NGO'))
    manager = models.ForeignKey(User, related_name="managed_projects",
        verbose_name=_('manager'))

    state = models.CharField(_('state'), choices=STATES, max_length=20)
    country = models.ForeignKey(Country, verbose_name=_('country'))
    location = models.CharField(_('location'), max_length=120)
    start = models.DateField(_('start date'))
    end = models.DateField(_('end date'))
    budget = models.DecimalField(_('budget'), max_digits=10, decimal_places=2)
    donated = models.DecimalField(_('donations currently totaling'), max_digits=10, decimal_places=2)
    description = models.TextField(_('description'))

    class Meta:
        verbose_name = _('project')
        verbose_name_plural = _('projects')

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('organisation_project_detail', (self.id,), {})

    def get_funding_rate(self):
        return ( self.donated * 100 ) / (self.budget)


class ProjectFile(CreateUpdateModel):
    def upload_path(self, filename):
        return 'uploads/projects/%s/files/%s' % (self.project.name.lower(), filename)

    project = models.ForeignKey(Project, related_name='files',
        verbose_name=_('project'))
    file = models.FileField(_('file'), upload_to=upload_path)
    title = models.CharField(_('title'), max_length=100)

    class Meta:
        verbose_name = _('project file')
        verbose_name_plural = _('project files')

    def __unicode__(self):
        return self.file.name

    def get_filename(self):
        return self.file.name.split('/')[-1]

    @models.permalink
    def get_delete_url(self):
        return ('organisation_project_delete_file', (), {'object_id': self.id, })
