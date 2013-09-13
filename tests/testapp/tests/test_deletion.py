from django.test import TestCase

from towel import deletion

from testapp.models import Person, EmailAddress


class DeletionTest(TestCase):
    def test_deletion(self):
        person = Person.objects.create()

        email = person.emailaddress_set.create()
        self.assertEqual(EmailAddress.objects.count(), 1)
        email.delete()
        self.assertEqual(EmailAddress.objects.count(), 0)
        email = person.emailaddress_set.create()
        self.assertEqual(EmailAddress.objects.count(), 1)
        with deletion.protect():
            email.delete()
        self.assertEqual(EmailAddress.objects.count(), 1)
        email.delete()
        self.assertEqual(EmailAddress.objects.count(), 0)
