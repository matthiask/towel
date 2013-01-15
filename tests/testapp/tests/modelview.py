from django.test import TestCase

from towel import deletion

from testapp.models import Person, EmailAddress


class ModelViewTest(TestCase):
    def test_list_view(self):
        for i in range(7):
            p = Person.objects.create(family_name='Family %r' % i)

        # paginate_by=5
        self.assertContains(self.client.get('/persons/'),
            'name="batch_', 5)
        self.assertContains(self.client.get('/persons/?page=2'),
            'name="batch_', 2)

        self.assertContains(self.client.get(p.get_absolute_url()),
            'Family 6')
        self.assertEqual(self.client.get('/persons/0/').status_code, 404)
        self.assertEqual(self.client.get('/persons/a/').status_code, 404)

    def test_crud(self):
        self.assertContains(self.client.get('/persons/add/'), '<form', 1)
        self.assertEqual(self.client.post('/persons/add/', {}).status_code,
            200)
        response = self.client.post('/persons/add/', {
            'family_name': 'Blub',
            'given_name': 'Blab',
            'created': '2013-01-01 01:00:00',
            })
        person = Person.objects.get()
        self.assertRedirects(response, person.get_absolute_url())
        self.assertContains(self.client.get(person.get_absolute_url()),
            'Blab Blub')
