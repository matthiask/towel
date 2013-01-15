from django.db import models

from towel import deletion
from towel.managers import SearchManager


class PersonManager(SearchManager):
    search_fields = ('family_name', 'given_name')


class Person(models.Model):
    family_name = models.CharField(max_length=100)
    given_name = models.CharField(max_length=100)

    objects = PersonManager()


class EmailManager(SearchManager):
    search_fields = ('person__family_name', 'person__given_name', 'email')


class EmailAddress(deletion.Model):
    person = models.ForeignKey(Person)
    email = models.EmailField()

    objects = EmailManager()
