from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext_lazy as _

from mooch.accounts.middleware import get_current_user

class CreateUpdateModel(models.Model):
    """
    Store timestamps for creation and last modification.
    """

    created = models.DateTimeField(_('Created'), auto_now_add=True)
    modified = models.DateTimeField(_('Modified'), auto_now=True)

    class Meta:
        abstract = True
        get_latest_by = 'created'
        ordering = ('created',)

class CreatorModel(CreateUpdateModel):
    """
    Store the currently logged-in user in addition to the timestamps above.
    """

    created_by = models.ForeignKey(User, related_name='created_%(class)s_set',
        default=get_current_user, verbose_name=_('Created by'))

    class Meta:
        abstract = True

class BaseModel(CreatorModel):
    """
    Often, we need a name and a notes field (which may be blank) for our
    objects.
    """

    name = models.CharField(_('Name'), max_length=100)
    notes = models.TextField(_('Notes'), blank=True)

    class Meta:
        abstract = True
        ordering = ('name',)

    def __unicode__(self):
        return self.name
    
#class ContentTypeMixin(models.Model):
#    """
#    Simplify some of the needed boilerplate code for objects which can
#    have a foreign key to any other object.
#    """
#
#    content_type = models.ForeignKey(ContentType)
#    object_id = models.PositiveIntegerField()
#    content_object = generic.GenericForeignKey()
#
#    class Meta:
#        abstract = True
#
#
#class ContentTypeManager(models.Manager):
#    def for_object_and_profile(self, obj, profile):
#        return self._for_object(obj, self.for_profile(profile))
#
#    def for_object(self, obj):
#        return self._for_object(obj, self.all())
#
#    def _for_object(self, obj, queryset):
#        """
#        Helper function which helps following reverse generic relations.
#        """
#
#        if isinstance(obj, models.Model):
#            return self.filter(
#                content_type=ContentType.objects.get_for_model(obj),
#                object_id=obj.pk)
#
#        # it's probably a model class, not an instance
#        return self.filter(
#            content_type=ContentType.objects.get_for_model(obj))
