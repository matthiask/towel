from django.core.urlresolvers import reverse
from django.utils.encoding import force_text
from django.test import TestCase

from testapp.models import Person, EmailAddress, Message


class ModelViewTest(TestCase):
    def test_list_view(self):
        for i in range(7):
            p = Person.objects.create(family_name='Family %r' % i)

        # paginate_by=5
        self.assertContains(
            self.client.get('/persons/'),
            'name="batch_', 5)
        self.assertContains(
            self.client.get('/persons/?page=2'),
            'name="batch_', 2)
        # Invalid page number -> first page
        self.assertContains(
            self.client.get('/persons/?page=abc'),
            'name="batch_', 5)
        # Empty page -> last page
        self.assertContains(
            self.client.get('/persons/?page=42'),
            'name="batch_', 2)
        # Everything
        self.assertContains(
            self.client.get('/persons/?all=1'),
            'name="batch_', 7)

        self.assertContains(
            self.client.get(p.get_absolute_url()),
            'Family 6')
        self.assertEqual(self.client.get('/persons/0/').status_code, 404)
        self.assertEqual(self.client.get('/persons/a/').status_code, 404)

    def test_crud(self):
        self.assertContains(self.client.get('/persons/add/'), '<form', 1)
        self.assertEqual(
            self.client.post('/persons/add/', {
                'family_name': '',
                'given_name': '',
                'emails-TOTAL_FORMS': 0,
                'emails-INITIAL_FORMS': 0,
                'emails-MAX_NUM_FORMS': 10,
            }).status_code,
            200)
        self.assertEqual(
            self.client.post('/persons/add/', {
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
        self.assertContains(
            self.client.get(person.get_absolute_url()),
            'Blab Blub')

        self.assertContains(
            self.client.get(person.urls['edit']),
            '<form', 1)
        response = self.client.post(person.urls['edit'], {
            'family_name': 'Blub',
            'given_name': 'Blabbba',
            'emails-TOTAL_FORMS': 0,
            'emails-INITIAL_FORMS': 0,
            'emails-MAX_NUM_FORMS': 10,
        })
        self.assertRedirects(response, person.get_absolute_url())
        self.assertContains(
            self.client.get(person.get_absolute_url()),
            'Blabbba Blub')

        # We still only have one person in the database
        self.assertEqual(force_text(Person.objects.get()), 'Blabbba Blub')

        # Open the deletion page
        response = self.client.get(person.urls['delete'])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Person.objects.count(), 1)
        self.assertRedirects(
            self.client.post(person.urls['delete']),
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
        self.assertRedirects(
            self.client.get(person.urls['delete']),
            person.urls['detail'])
        response = self.client.post(person.urls['delete'])
        self.assertRedirects(response, person.urls['detail'])
        # Nothing has been deleted
        self.assertEqual(Person.objects.count(), 1)
        self.assertTrue(
            ('Deletion not allowed: There are email addresses related'
                ' to this object.') in str(response.cookies))

        # Add another email address
        self.assertRedirects(
            self.client.post(person.urls['edit'], {
                'family_name': 'Blub',
                'given_name': 'Blab',
                'emails-TOTAL_FORMS': 2,
                'emails-INITIAL_FORMS': 1,
                'emails-MAX_NUM_FORMS': 10,
                'emails-0-email': 'test1@example.com',
                'emails-0-id': emailaddress.id,
                'emails-1-email': 'test2@example.com',
            }),
            person.urls['detail'],
        )

        self.assertEqual(
            sorted(person.emailaddress_set.values_list('email', flat=True)),
            ['test1@example.com', 'test2@example.com'],
        )

        emailaddresses = list(person.emailaddress_set.order_by('id'))
        emailaddresses[0].message_set.create(message='Save me')

        # Try deleting both email addresses; deleting the first should fail
        # because of bound message instances.
        self.assertRedirects(
            self.client.post(person.urls['edit'], {
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
            }),
            person.urls['detail'],
        )

        self.assertEqual(
            sorted(person.emailaddress_set.values_list('email', flat=True)),
            ['test1@example.com'],
        )
        # However, editing the person instance should have succeeded
        self.assertContains(
            self.client.get(person.urls['detail']),
            'Blab Blubbber')

    def test_modelviewurls(self):
        person = Person.objects.create()

        self.assertEqual(
            person.urls['detail'],
            '/persons/%s/' % person.pk)
        self.assertEqual(
            person.urls['edit'],
            '/persons/%s/edit/' % person.pk)
        self.assertEqual(
            person.urls['delete'],
            '/persons/%s/delete/' % person.pk)
        self.assertEqual(
            person.urls['list'],
            '/persons/')

        self.assertEqual(reverse('testapp_person_list'), '/persons/')
        self.assertEqual(
            reverse('testapp_person_detail', kwargs={'pk': person.pk}),
            person.get_absolute_url(),
        )

    def test_emailaddress_views(self):
        emailaddress = EmailAddress.objects.create(
            person=Person.objects.create(
                given_name='Testa',
                family_name='Testi',
            ),
            email='test@example.com',
        )

        response = self.client.get(emailaddress.get_absolute_url())
        self.assertContains(response, 'Testa Testi')
        # <title>, <h2>, <table>
        self.assertContains(response, 'test@example.com', 3)
        self.assertContains(
            response,
            reverse('testapp_person_detail', kwargs={
                'pk': emailaddress.person_id,
            }),
        )

        list_url = reverse('testapp_emailaddress_list')

        response = self.client.get(list_url)
        self.assertContains(
            response,
            '<a href="/emailaddresses/%s/">test@example.com</a>' % (
                emailaddress.pk))
        self.assertContains(
            response,
            '<a href="/persons/%s/">Testa Testi</a>' % emailaddress.person_id)

        for i in range(10):
            EmailAddress.objects.create(
                person=Person.objects.create(
                    given_name='Testa',
                    family_name='Testi',
                    is_active=bool(i % 2),
                ),
                email='test%s@example.com' % i,
            )

        # The EmailAddressSearchForm defaults to only showing email addresses
        # of active persons.
        self.assertContains(
            self.client.get(list_url),
            '<span>1 - 5 / 6</span>',
        )
        self.assertContains(
            self.client.get(list_url + '?person__is_active=1'),
            '<span>1 - 5 / 11</span>',
        )
        self.assertContains(
            self.client.get(list_url + '?person__is_active=3'),
            '<span>1 - 5 / 5</span>',
        )

        # Multiple choice it up a bit.
        self.assertContains(
            self.client.get(
                list_url +
                '?person__relationship=married&person__relationship=divorced',
            ),
            '<span>0 - 0 / 0</span>',
        )

    def test_batchform(self):
        for i in range(20):
            Person.objects.create(
                given_name='Given %s' % i,
                family_name='Family %s' % i,
            )

        self.assertContains(
            self.client.get('/persons/'),
            '<span>1 - 5 / 20</span>')

        response = self.client.post('/persons/', {
            'batchform': 1,
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            '<ul class="errorlist"><li>No items selected</li></ul>')

        self.assertEqual(Person.objects.filter(is_active=False).count(), 0)
        data = {
            'batchform': 1,
            'batch-is_active': 3,
        }
        for pk in Person.objects.values_list('id', flat=True)[:3]:
            data['batch_%s' % pk] = pk
        response = self.client.post('/persons/', data)
        self.assertRedirects(response, '/persons/')

        cookies = str(response.cookies)
        self.assertTrue('3 have been updated.' in cookies)
        self.assertTrue('Given 0 Family 0' in cookies)
        self.assertTrue('Given 1 Family 1' in cookies)
        self.assertTrue('Given 10 Family 10' in cookies)
        self.assertEqual(Person.objects.filter(is_active=False).count(), 3)

    def test_automatic_get_absolute_url(self):
        self.assertTrue(hasattr(Message, 'get_absolute_url'))
        message = Message.objects.create(
            sent_to=EmailAddress.objects.create(
                person=Person.objects.create()
            ),
        )

        self.assertEqual(
            message.get_absolute_url(),
            '/messages/%s/' % message.pk)
