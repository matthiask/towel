from django.core.urlresolvers import reverse
from django.utils.encoding import force_text
from django.test import TestCase

from testapp.models import Resource


class ResourceTest(TestCase):
    def test_list_view(self):
        for i in range(7):
            r = Resource.objects.create(name='Resource {}'.format(i))

        # paginate_by=5
        self.assertContains(
            self.client.get('/resources/'),
            'name="batch_', 5)
        self.assertContains(
            self.client.get('/resources/?page=2'),
            'name="batch_', 2)
        # Invalid page number -> first page
        self.assertContains(
            self.client.get('/resources/?page=abc'),
            'name="batch_', 5)
        # Empty page -> last page
        self.assertContains(
            self.client.get('/resources/?page=42'),
            'name="batch_', 2)

        self.assertContains(
            self.client.get(r.get_absolute_url()),
            'Resource 6')
        self.assertEqual(self.client.get('/resources/0/').status_code, 404)
        self.assertEqual(self.client.get('/resources/a/').status_code, 404)

    def test_crud(self):
        self.assertContains(self.client.get('/resources/add/'), '<form', 1)
        self.assertEqual(
            self.client.post('/resources/add/', {
                'name': '',
            }).status_code,
            200)
        self.assertEqual(
            self.client.post('/resources/add/', {
                # Should not validate because of StrippedTextInput
                'name': ' ',
            }).status_code,
            200)
        response = self.client.post('/resources/add/', {
            'name': 'Blub',
        })
        resource = Resource.objects.get()
        self.assertRedirects(response, resource.get_absolute_url())
        self.assertContains(
            self.client.get(resource.get_absolute_url()),
            'Blub')

        self.assertContains(
            self.client.get(resource.urls['edit']),
            '<form', 1)
        response = self.client.post(resource.urls['edit'], {
            'name': 'Blabbba',
        })
        self.assertRedirects(response, resource.get_absolute_url())
        self.assertContains(
            self.client.get(resource.get_absolute_url()),
            'Blabbba')

        # We still only have one resource in the database
        self.assertEqual(force_text(Resource.objects.get()), 'Blabbba')

        # Open the deletion page
        response = self.client.get(resource.urls['delete'])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Resource.objects.count(), 1)
        self.assertRedirects(
            self.client.post(resource.urls['delete']),
            '/resources/')
        self.assertEqual(Resource.objects.count(), 0)

    def test_modelviewurls(self):
        resource = Resource.objects.create()

        self.assertEqual(
            resource.urls['detail'],
            '/resources/%s/' % resource.pk)
        self.assertEqual(
            resource.urls['edit'],
            '/resources/%s/edit/' % resource.pk)
        self.assertEqual(
            resource.urls['delete'],
            '/resources/%s/delete/' % resource.pk)
        self.assertEqual(
            resource.urls['list'],
            '/resources/')

        self.assertEqual(reverse('testapp_resource_list'), '/resources/')
        self.assertEqual(
            reverse('testapp_resource_detail', kwargs={'pk': resource.pk}),
            resource.get_absolute_url(),
        )

    def test_batchform(self):
        for i in range(20):
            Resource.objects.create(
                name='Resource %s' % i,
            )

        self.assertContains(
            self.client.get('/resources/'),
            '<span>1 - 5 / 20</span>')

        response = self.client.post('/resources/', {
            'batchform': 1,
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            '<ul class="errorlist"><li>No items selected</li></ul>')

        self.assertEqual(Resource.objects.filter(is_active=False).count(), 0)
        data = {
            'batchform': 1,
            'batch-action': 'set_active',
        }
        for pk in Resource.objects.values_list('id', flat=True)[:3]:
            data['batch_%s' % pk] = pk
        response = self.client.post('/resources/', data)
        self.assertContains(response, 'Set active')
        self.assertContains(
            response,
            '<option value="1" selected="selected">Unknown</option>')
        data['confirm'] = 1
        data['is_active'] = 3
        response = self.client.post('/resources/', data)
        self.assertRedirects(response, '/resources/')

        cookies = str(response.cookies)
        self.assertTrue('3 have been updated.' in cookies)
        self.assertTrue('Resource 0' in cookies)
        self.assertTrue('Resource 1' in cookies)
        self.assertTrue('Resource 2' in cookies)
        self.assertEqual(Resource.objects.filter(is_active=False).count(), 3)
