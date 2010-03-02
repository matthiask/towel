from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from countries.models import Country

from mooch.accounts.middleware import get_current_user
from mooch.abstract.models import BaseModel, CreateUpdateModel

class NGO(BaseModel):
    full_name = models.CharField(_('Elaborate name'), max_length=100)
    logo = models.ImageField(_('Logo'), upload_to='img/upload/logos')
    homepage = models.URLField(_('Homepage'), verify_exists=False)
    
    # maybe we need some kind of overall contact person?
    
    # payment account? 
    

def get_current_ngo():
    try:
        return get_current_user().get_profile().ngo
    except:
        return None


class Project(CreateUpdateModel):
    STATES = (
        ('PLANING', _('In planing')),
        ('FUNDRAISING', _('Found raising')),
        ('REALISATION', _('In realisation')),
        ('FINISHED', _('Finished')),
    )
    
    name = models.CharField(_('Name'), max_length=100)
    ngo = models.ForeignKey(NGO, default=get_current_ngo )
    manager = models.ForeignKey(User, related_name="managed_projects")

    state = models.CharField(_('Project state'), choices=STATES, max_length=20)
    country = models.ForeignKey(Country)
    location = models.CharField(_('Location'), max_length=120)
    start = models.DateField(_('Start date'))
    end = models.DateField(_('End date'))
    budget = models.DecimalField(_('Project budget'), max_digits=10, decimal_places=2)
    donated = models.DecimalField(_('Donations currently totaling'), max_digits=10, decimal_places=2)
    description = models.TextField(_('Description'))
    
    def __unicode__(self):
        return self.name
    
    @models.permalink
    def get_absolute_url(self):
        return ('organisation_project_detail', (), {'object_id': self.id, })
    
    def get_funding_rate(self):
        return ( self.donated * 100 ) / (self.budget)
    
class ProjectFile(CreateUpdateModel):
    
    def upload_path(self, filename):
        return 'uploads/projects/%s/files/%s' % (self.project.name.lower(), filename)
    
    project = models.ForeignKey(Project, related_name='files')
    file = models.FileField(_('file'), upload_to=upload_path)
                            
    def get_filename(self):
        return self.file.name.split('/')[-1]
    
    @models.permalink
    def get_delete_url(self):
        return ('organisation_project_delete_file', (), {'object_id': self.id, })