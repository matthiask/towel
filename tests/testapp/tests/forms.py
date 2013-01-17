import json

from django.test import TestCase

from towel import deletion
from towel.forms import WarningsForm

from testapp.models import Person, EmailAddress, Message


class FormsTest(TestCase):
    def test_warningsform(self):
        person = Person.objects.create()
        emailaddress = person.emailaddress_set.create()

        self.assertEqual(self.client.get(person.urls['message']).status_code,
            200)
        self.assertEqual(self.client.post(person.urls['message']).status_code,
            200)

        response = self.client.post(person.urls['message'], {
            'sent_to': emailaddress.pk,
            'message': 'Hallo Welt',
            })
        self.assertRedirects(response, person.urls['detail'])
        self.assertEqual(Message.objects.count(), 1)

        response = self.client.post(person.urls['message'], {
            'sent_to': emailaddress.pk,
            'message': '   ',
            })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please review the following warnings:')

        response = self.client.post(person.urls['message'], {
            'sent_to': emailaddress.pk,
            'message': '   ',
            'ignore_warnings': 1,
            })
        self.assertRedirects(response, person.urls['detail'])
        self.assertEqual(Message.objects.count(), 2)


# TODO quick rules test
# TODO autocompletion widget tests?
