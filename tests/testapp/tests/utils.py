from django.test import TestCase

from towel.utils import related_classes

from testapp.models import Person, EmailAddress


class UtilsTest(TestCase):
    def test_related_classes(self):
        """Test the functionality of towel.utils.related_classes"""
        person = Person.objects.create(
            family_name='Muster',
            given_name='Hans',
            )
        EmailAddress.objects.create(
            person=person,
            email='hans@example.com',
            )

        self.assertEqual(
            set(related_classes(person)),
            set((Person, EmailAddress)),
            )
