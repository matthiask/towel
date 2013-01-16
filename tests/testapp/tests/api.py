import json

from django.test import TestCase

from towel import deletion

from testapp.models import Person, EmailAddress, Message


class APITest(TestCase):
    def setUp(self):
        for i in range(100):
            person = Person.objects.create(
                given_name='Given %s' % i,
                family_name='Given %s' % i,
                )
            person.emailaddress_set.create(email='test%s@example.com' % i)
        self.api = json.loads(self.client.get(
            '/api/v1/',
            HTTP_ACCEPT='application/json',
            ).content)

    def get_json(self, uri):
        try:
            response = self.client.get(
                uri,
                HTTP_ACCEPT='application/json',
                )
            return json.loads(response.content)
        except ValueError:
            print uri, response.status_code, response.content

    def test_info(self):
        self.assertEqual(self.client.get('/api/v1/').status_code, 406)
        response = self.client.get('/api/v1/',
            HTTP_ACCEPT='application/json',
            )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        self.assertEqual(data['__str__'], 'v1')
        self.assertEqual(data['__uri__'], 'http://testserver/api/v1/')
        self.assertEqual(len(data['resources']), 3)
        self.assertEqual(data['person']['__uri__'],
            'http://testserver/api/v1/person/')
        self.assertEqual(data['emailaddress']['__uri__'],
            'http://testserver/api/v1/emailaddress/')
        self.assertEqual(data['message']['__uri__'],
            'http://testserver/api/v1/message/')

    def test_list_detail(self):
        person_uri = self.api['person']['__uri__']
        data = self.get_json(person_uri)

        self.assertEqual(len(data['objects']), 20)
        self.assertEqual(data['meta'], {
            u'limit': 20,
            u'next': u'http://testserver/api/v1/person/?limit=20&offset=20',
            u'offset': 0,
            u'previous': None,
            u'total': 100,
            })

        first = Person.objects.order_by('id')[0]
        first_person = data['objects'][0]
        correct = {
            'id': first.pk,
            '__pk__': first.pk,
            '__pretty__': {},
            '__str__': 'Given 0 Given 0',
            '__uri__': 'http://testserver/api/v1/person/%s/' % first.pk,
            'family_name': 'Given 0',
            'given_name': 'Given 0',
            }

        for key, value in correct.items():
            self.assertEqual(first_person[key], value)


        self.assertEqual(
            len(self.get_json(person_uri + '?limit=100')['objects']),
            100,
            )
        self.assertEqual(
            len(self.get_json(person_uri + '?limit=200')['objects']),
            100,
            )
        self.assertEqual(
            len(self.get_json(person_uri + '?limit=100&offset=50')['objects']),
            50,
            )

        data = self.get_json(first_person['__uri__'] + '?full=1')
        for key, value in correct.items():
            self.assertEqual(data[key], value)

        data = self.get_json(self.api['emailaddress']['__uri__'])
        first_email = data['objects'][0]
        self.assertEqual(data['meta']['total'], 100)
        self.assertEqual(first_email['email'], 'test0@example.com')

        data = self.get_json(first_email['__uri__'])
        self.assertEqual(data['person'], first_person['__uri__'])

        data = self.get_json(first_email['__uri__'] + '?full=1')
        self.assertEqual(data['person'], first_person)

        # Sets
        persons = ';'.join(str(person.pk) for person
            in Person.objects.all()[:5])
        data = self.get_json(person_uri + '%s/' % persons)

        self.assertFalse('meta' in data)
        self.assertEqual(len(data['objects']), 5)

        self.assertEqual(
            self.get_json(person_uri + '0;/'),
            {u'error': u'Some objects do not exist.'},
            )
        self.assertEqual(
            self.get_json(person_uri + '0/'),
            {u'error': u'No Person matches the given query.'},
            )
