from django.db import models
from django.utils.timezone import now

from towel import deletion
from towel.managers import SearchManager
from towel.modelview import ModelViewURLs


class PersonManager(SearchManager):
    search_fields = ('family_name', 'given_name')


class Person(models.Model):
    created = models.DateTimeField(default=now)
    family_name = models.CharField(max_length=100)
    given_name = models.CharField(max_length=100)

    objects = PersonManager()
    urls = ModelViewURLs(lambda obj: {'pk': obj.pk})

    def __unicode__(self):
        return u'%s %s' % (self.given_name, self.family_name)

    def get_absolute_url(self):
        return self.urls['detail']


class EmailManager(SearchManager):
    search_fields = ('person__family_name', 'person__given_name', 'email')


class EmailAddress(deletion.Model):
    person = models.ForeignKey(Person)
    email = models.EmailField()

    objects = EmailManager()
    urls = ModelViewURLs(lambda obj: {'pk': obj.pk})

    def __unicode__(self):
        return self.email

    def get_absolute_url(self):
        return self.urls['detail']
