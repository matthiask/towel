from django.db import models
from django.utils.timezone import now

from towel import deletion
from towel.managers import SearchManager
from towel.modelview import ModelViewURLs
from towel.resources.urls import model_resource_urls


class Group(models.Model):
    name = models.CharField(max_length=100)


class PersonManager(SearchManager):
    search_fields = ("family_name", "given_name")


class Person(models.Model):
    RELATIONSHIP_CHOICES = (
        ("", "unspecified"),
        ("single", "single"),
        ("relation", "in a relationship"),
        ("married", "married"),
        ("divorced", "divorced"),
    )

    created = models.DateTimeField(default=now)
    is_active = models.BooleanField(default=True)
    family_name = models.CharField(max_length=100)
    given_name = models.CharField(max_length=100)
    relationship = models.CharField(
        max_length=20, blank=True, choices=RELATIONSHIP_CHOICES
    )
    groups = models.ManyToManyField(Group, related_name="members")

    objects = PersonManager()
    urls = ModelViewURLs(lambda obj: {"pk": obj.pk})

    class Meta:
        ordering = ["family_name", "given_name"]

    def __str__(self):
        return f"{self.given_name} {self.family_name}"

    def get_absolute_url(self):
        return self.urls["detail"]


class EmailManager(SearchManager):
    search_fields = ("person__family_name", "person__given_name", "email")


class EmailAddress(deletion.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    email = models.EmailField()

    objects = EmailManager()
    urls = ModelViewURLs(lambda obj: {"pk": obj.pk})

    class Meta:
        ordering = ["email"]
        verbose_name = "email address"
        verbose_name_plural = "email addresses"

    def __str__(self):
        return self.email

    def get_absolute_url(self):
        return self.urls["detail"]


class Message(models.Model):
    """
    This model is used to test the behavior of
    ``save_formset_deletion_allowed_if_only``. The presence of message
    instances should protect email addresses from getting deleted.
    """

    sent_to = models.ForeignKey(EmailAddress, on_delete=models.CASCADE)
    message = models.TextField()

    # No get_absolute_url method on purpose; is automatically added by
    # ModelView

    class Meta:
        ordering = ["id"]


class ResourceManager(SearchManager):
    search_fields = ("name",)


@model_resource_urls()
class Resource(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    objects = ResourceManager()

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name
