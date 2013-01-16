from django.core.urlresolvers import reverse
from django.test import TestCase

from towel import deletion

from testapp.models import Person, EmailAddress, Message


class ModelViewTest(TestCase):
    def test_list_view(self):
        for i in range(7):
            p = Person.objects.create(family_name='Family %r' % i)

        # paginate_by=5
        self.assertContains(self.client.get('/persons/'),
            'name="batch_', 5)
        self.assertContains(self.client.get('/persons/?page=2'),
            'name="batch_', 2)
        # Invalid page number -> first page
        self.assertContains(self.client.get('/persons/?page=abc'),
            'name="batch_', 5)
        # Empty page -> last page
        self.assertContains(self.client.get('/persons/?page=42'),
            'name="batch_', 2)
        # Everything
        self.assertContains(self.client.get('/persons/?all=1'),
            'name="batch_', 7)

        self.assertContains(self.client.get(p.get_absolute_url()),
            'Family 6')
        self.assertEqual(self.client.get('/persons/0/').status_code, 404)
        self.assertEqual(self.client.get('/persons/a/').status_code, 404)

    def test_crud(self):
        self.assertContains(self.client.get('/persons/add/'), '<form', 1)
        self.assertEqual(self.client.post('/persons/add/', {
            'family_name': '',
            'given_name': '',
            'emails-TOTAL_FORMS': 0,
            'emails-INITIAL_FORMS': 0,
            'emails-MAX_NUM_FORMS': 10,
            }).status_code,
            200)
        self.assertEqual(self.client.post('/persons/add/', {
            # Should not validate because of StrippedTextInput
            'family_name': ' ',
            'given_name': ' ',
            'emails-TOTAL_FORMS': 0,
            'emails-INITIAL_FORMS': 0,
            'emails-MAX_NUM_FORMS': 10,
            }).status_code,
            200)
        response = self.client.post('/persons/add/', {
            'family_name': 'Blub',
            'given_name': 'Blab',
            'emails-TOTAL_FORMS': 0,
            'emails-INITIAL_FORMS': 0,
            'emails-MAX_NUM_FORMS': 10,
            })
        person = Person.objects.get()
        self.assertRedirects(response, person.get_absolute_url())
        self.assertContains(self.client.get(person.get_absolute_url()),
            'Blab Blub')

        self.assertContains(self.client.get(person.urls['edit']),
            '<form', 1)
        response = self.client.post(person.urls['edit'], {
            'family_name': 'Blub',
            'given_name': 'Blabbba',
            'emails-TOTAL_FORMS': 0,
            'emails-INITIAL_FORMS': 0,
            'emails-MAX_NUM_FORMS': 10,
            })
        self.assertRedirects(response, person.get_absolute_url())
        self.assertContains(self.client.get(person.get_absolute_url()),
            'Blabbba Blub')

        # We still only have one person in the database
        self.assertEqual(unicode(Person.objects.get()), 'Blabbba Blub')

        # Open the deletion page
        response = self.client.get(person.urls['delete'])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Person.objects.count(), 1)
        self.assertRedirects(self.client.post(person.urls['delete']),
            '/persons/')
        self.assertEqual(Person.objects.count(), 0)

    def test_crud_formsets(self):
        response = self.client.post('/persons/add/', {
            'family_name': 'Blub',
            'given_name': 'Blab',
            'emails-TOTAL_FORMS': 1,
            'emails-INITIAL_FORMS': 0,
            'emails-MAX_NUM_FORMS': 10,
            'emails-0-email': 'test@example.com',
            })
        person = Person.objects.get()
        emailaddress = person.emailaddress_set.get()
        self.assertEqual(emailaddress.email, 'test@example.com')

        # Deleting the person should not work because of the email addresses
        self.assertRedirects(self.client.get(person.urls['delete']),
            person.urls['detail'])
        response = self.client.post(person.urls['delete'])
        self.assertRedirects(response, person.urls['detail'])
        # Nothing has been deleted
        self.assertEqual(Person.objects.count(), 1)
        self.assertTrue(
            ('Deletion not allowed: There are email addresses related'
                ' to this object.') in str(response.cookies))

        # Add another email address
        self.assertRedirects(self.client.post(person.urls['edit'], {
            'family_name': 'Blub',
            'given_name': 'Blab',
            'emails-TOTAL_FORMS': 2,
            'emails-INITIAL_FORMS': 1,
            'emails-MAX_NUM_FORMS': 10,
            'emails-0-email': 'test1@example.com',
            'emails-0-id': emailaddress.id,
            'emails-1-email': 'test2@example.com',
            }), person.urls['detail'])

        self.assertEqual(
            sorted(person.emailaddress_set.values_list('email', flat=True)),
            ['test1@example.com', 'test2@example.com'],
            )

        emailaddresses = list(person.emailaddress_set.order_by('id'))
        emailaddresses[0].message_set.create(message='Save me')

        # Try deleting both email addresses; deleting the first should fail
        # because of bound message instances.
        self.assertRedirects(self.client.post(person.urls['edit'], {
            'family_name': 'Blubbber',
            'given_name': 'Blab',
            'emails-TOTAL_FORMS': 2,
            'emails-INITIAL_FORMS': 2,
            'emails-MAX_NUM_FORMS': 10,
            'emails-0-email': 'test1@example.com',
            'emails-0-id': emailaddresses[0].id,
            'emails-0-DELETE': 1,
            'emails-1-email': 'test2@example.com',
            'emails-1-id': emailaddresses[1].id,
            'emails-1-DELETE': 1,
            }), person.urls['detail'])

        self.assertEqual(
            sorted(person.emailaddress_set.values_list('email', flat=True)),
            ['test1@example.com'],
            )
        # However, editing the person instance should have succeeded
        self.assertContains(self.client.get(person.urls['detail']),
            'Blab Blubbber')

    def test_modelviewurls(self):
        person = Person.objects.create()

        self.assertEqual(person.urls['detail'],
            '/persons/%s/' % person.pk)
        self.assertEqual(person.urls['edit'],
            '/persons/%s/edit/' % person.pk)
        self.assertEqual(person.urls['delete'],
            '/persons/%s/delete/' % person.pk)
        self.assertEqual(person.urls['list'],
            '/persons/')

        self.assertEqual(reverse('testapp_person_list'), '/persons/')
        self.assertEqual(
            reverse('testapp_person_detail', kwargs={'pk': person.pk}),
            person.get_absolute_url(),
            )
