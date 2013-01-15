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
