import json

from django.core.urlresolvers import NoReverseMatch
from django.test import TestCase

from towel import deletion
from towel.api import api_reverse

from testapp.models import Group, Person, EmailAddress, Message


class APITest(TestCase):
    def setUp(self):
        for i in range(100):
            person = Person.objects.create(
                given_name='Given %s' % i,
                family_name='Family %s' % i,
                )
            person.emailaddress_set.create(email='test%s@example.com' % i)
        self.api = self.get_json('/api/v1/')

    def get_json(self, uri, status_code=200):
        try:
            response = self.client.get(
                uri,
                HTTP_ACCEPT='application/json',
                )
            self.assertEqual(response.status_code, status_code)
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
        self.assertEqual(len(data['resources']), 4)
        self.assertEqual(data['person']['__uri__'],
            'http://testserver/api/v1/person/')
        self.assertEqual(data['emailaddress']['__uri__'],
            'http://testserver/api/v1/emailaddress/')
        self.assertEqual(data['message']['__uri__'],
            'http://testserver/api/v1/message/')
        self.assertEqual(data['group']['__uri__'],
            'http://testserver/api/v1/group/')

        self.assertEqual(len(data['views']), 1)

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
            '__pretty__': {
                'relationship': 'unspecified',
                },
            '__str__': 'Given 0 Family 0',
            '__uri__': 'http://testserver/api/v1/person/%s/' % first.pk,
            'family_name': 'Family 0',
            'given_name': 'Given 0',
            'relationship': '',
            }

        for key, value in correct.items():
            self.assertEqual(first_person[key], value)
        self.assertTrue('is_active' not in first_person)

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
            self.get_json(person_uri + '0;/', status_code=404),
            {u'error': u'Some objects do not exist.'},
            )
        self.assertEqual(
            self.get_json(person_uri + '0/', status_code=404),
            {u'error': u'No Person matches the given query.'},
            )

    def test_http_methods(self):
        response = self.client.options('/api/v1/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Allow'], 'GET, HEAD, OPTIONS')

        response = self.client.post('/api/v1/')
        self.assertEqual(response.status_code, 406)

        response = self.client.options(self.api['person']['__uri__'])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Allow'], 'GET, HEAD, OPTIONS')

        response = self.client.post('/api/v1/person/',
            HTTP_ACCEPT='application/json',
            )
        self.assertEqual(response.status_code, 405)

    def test_post_message(self):
        person = Person.objects.create()
        emailaddress = person.emailaddress_set.create()

        response = self.client.post('/api/v1/message/')
        self.assertEqual(response.status_code, 406)

        response = self.client.post('/api/v1/message/', {
            }, HTTP_ACCEPT='application/json')
        data = json.loads(response.content)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data['error'], u'Validation failed')
        self.assertEqual(data['form']['message'],
            [u'This field is required.'])
        self.assertEqual(data['form']['sent_to'],
            [u'This field is required.'])

        response = self.client.post('/api/v1/message/', {
            'message': 'Blabla',
            'sent_to': emailaddress.pk,
            }, HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 201)
        message = Message.objects.get()
        data = self.get_json(response['Location'])
        self.assertEqual(data['__pk__'], message.pk)

        response = self.client.post('/api/v1/message/', json.dumps({
            'message': 'Blabla',
            'sent_to': emailaddress.pk,
            }), 'application/json', HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 201)
        message = Message.objects.latest('pk')
        data = self.get_json(response['Location'])
        self.assertEqual(data['__pk__'], message.pk)

        self.assertEqual(Message.objects.count(), 2)

    def test_unsupported_content_type(self):
        response = self.client.post('/api/v1/message/', {
            })

        response = self.client.post('/api/v1/message/',
            'blabla',
            'application/octet-stream',  # Unsupported
            HTTP_ACCEPT='application/json',
            )
        self.assertEqual(response.status_code, 415)

    def test_info_view(self):
        response = self.client.get('/api/v1/info/',
            HTTP_ACCEPT='application/json')
        data = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['hello'], 'World!')
        self.assertEqual(data['method'], 'GET')

        response = self.client.post('/api/v1/info/', {
            'bla': 'blaaa',
            }, HTTP_ACCEPT='application/json')
        data = json.loads(response.content)
        self.assertEqual(data['data']['bla'], 'blaaa')

        response = self.client.post('/api/v1/info/', json.dumps({
            'bla': 'blaaa',
            }), 'application/json', HTTP_ACCEPT='application/json')
        data = json.loads(response.content)
        self.assertEqual(data['data']['bla'], 'blaaa')

        response = self.client.put('/api/v1/info/', json.dumps({
            'bla': 'blaaa',
            }), 'application/json', HTTP_ACCEPT='application/json')
        data = json.loads(response.content)
        self.assertEqual(data['method'], 'PUT')
        self.assertEqual(data['data']['bla'], 'blaaa')

        response = self.client.delete('/api/v1/info/',
            HTTP_ACCEPT='application/json')
        data = json.loads(response.content)
        self.assertEqual(data['method'], 'DELETE')

    def test_api_reverse(self):
        person = Person.objects.create()
        self.assertEqual(
            api_reverse(Person, 'list', api_name='v1'),
            '/api/v1/person/',
            )
        self.assertEqual(
            api_reverse(Person, 'detail', api_name='v1', pk=person.pk),
            '/api/v1/person/%s/' % person.pk,
            )
        self.assertEqual(
            api_reverse(person, 'detail', api_name='v1', pk=person.pk),
            '/api/v1/person/%s/' % person.pk,
            )
        self.assertEqual(
            api_reverse(Person, 'set', api_name='v1', pks='2;3;4'),
            '/api/v1/person/2;3;4/',
            )
        self.assertEqual(
            api_reverse(Person, 'sets', api_name='v1', pks='2;3;4',
                fail_silently=True),
            None,
            )
        self.assertRaises(NoReverseMatch, api_reverse,
            Person, 'sets', api_name='v1', pks='2;')

    def test_serialization(self):
        from pprint import pprint
        person = Person.objects.order_by('id')[0]
        group = Group.objects.create(
            name='grouup',
            )
        person.groups.add(group)
        person.emailaddress_set.create(email='another@example.com')

        person_uri = api_reverse(person, 'detail', api_name='v1',
            pk=person.id)

        self.assertEqual(person.groups.count(), 1)
        self.assertEqual(person.emailaddress_set.count(), 2)

        data = self.get_json(person_uri)
        self.assertEqual(data['given_name'], 'Given 0')
        self.assertEqual(data['family_name'], 'Family 0')
        self.assertFalse('emailaddress_set' in data)
        self.assertFalse('groups' in data)

        data = self.get_json(person_uri + '?full=1')
        self.assertTrue('emailaddress_set' in data)
        self.assertTrue('groups' in data)

        data = self.get_json(self.api['group']['__uri__'])
        self.assertEqual(
            len(data['objects']),
            1)
        group_uri = data['objects'][0]['__uri__']

        data = self.get_json(group_uri)
        self.assertEqual(data['name'], 'grouup')
        self.assertFalse('members' in data)

        data = self.get_json(group_uri + '?full=1')
        self.assertEqual(data['name'], 'grouup')
        self.assertTrue('members' in data)
        self.assertEqual(len(data['members']), 1)
