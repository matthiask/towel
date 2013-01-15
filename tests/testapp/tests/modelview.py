from django.test import TestCase

from towel import deletion

from testapp.models import Person, EmailAddress


class ModelViewTest(TestCase):
    def test_list_view(self):
        Person.objects.create()
        Person.objects.create()
        Person.objects.create()
        Person.objects.create()
        Person.objects.create()
        Person.objects.create()
        Person.objects.create()

        # paginate_by=5
        self.assertContains(self.client.get('/persons/'),
            'name="batch_', 5)
        self.assertContains(self.client.get('/persons/?page=2'),
            'name="batch_', 2)
