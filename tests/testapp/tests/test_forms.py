from datetime import timedelta

from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils import timezone

from testapp.models import Person, Message


class FormsTest(TestCase):
    def test_warningsform(self):
        person = Person.objects.create()
        emailaddress = person.emailaddress_set.create()

        self.assertEqual(
            self.client.get(person.urls['message']).status_code,
            200)
        self.assertEqual(
            self.client.post(person.urls['message']).status_code,
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

    def test_searchform(self):
        date = timezone.now().replace(year=2012, month=10, day=1)

        for i in range(100):
            Person.objects.create(
                given_name='Given %s' % i,
                family_name='Family %s' % i,
                is_active=bool(i % 3),
                created=date + timedelta(days=i),
            )

        list_url = reverse('testapp_person_list')

        self.assertContains(
            self.client.get(list_url),
            '<span>1 - 5 / 100</span>',
        )
        self.assertContains(
            self.client.get(list_url + '?query=42'),
            '<span>1 - 1 / 1</span>',
        )
        self.assertContains(
            self.client.get(list_url + '?query=is:active'),
            '<span>1 - 5 / 66</span>',
        )
        self.assertContains(
            self.client.get(list_url + '?query=is:inactive'),
            '<span>1 - 5 / 34</span>',
        )
        self.assertContains(
            self.client.get(list_url + '?query=active:yes'),
            '<span>1 - 5 / 66</span>',
        )
        self.assertContains(
            self.client.get(list_url + '?query=active:off'),
            '<span>1 - 5 / 34</span>',
        )
        self.assertContains(
            self.client.get(list_url + '?query=year:2012'),
            '<span>1 - 5 / 92</span>',
        )
        self.assertContains(
            self.client.get(list_url + '?query="Given+1"+year%3A2012'),
            '<span>1 - 5 / 11</span>',
        )
        self.assertContains(
            self.client.get(list_url + '?query="%2BGiven+1"+year%3A2012'),
            '<span>1 - 5 / 11</span>',
        )
        self.assertContains(
            self.client.get(list_url + '?query="-Given+1"+year%3A2012'),
            '<span>1 - 5 / 81</span>',
        )

        # Form field
        self.assertContains(
            self.client.get(list_url + '?is_active=1'),
            '<span>1 - 5 / 100</span>',
        )
        self.assertContains(
            self.client.get(list_url + '?is_active=2'),
            '<span>1 - 5 / 66</span>',
        )
        self.assertContains(
            self.client.get(list_url + '?is_active=3'),
            '<span>1 - 5 / 34</span>',
        )

        # Invalid query
        self.assertRedirects(
            self.client.get(list_url + '?created__year=abc'),
            list_url + '?clear=1',
        )

        # Mixed quick (only inactive) and form field (only active)
        # Form field takes precedence
        self.assertContains(
            self.client.get(list_url + '?is_active=2&query=is:inactive'),
            '<span>1 - 5 / 66</span>',
        )

        # Search form persistence
        self.assertContains(
            self.client.get(list_url + '?s=1&is_active=3'),
            '<span>1 - 5 / 34</span>',
        )
        self.assertContains(
            self.client.get(list_url),
            '<span>1 - 5 / 34</span>',
        )
        self.assertContains(
            self.client.get(list_url + '?clear=1'),
            '<span>1 - 5 / 100</span>',
        )

        # Ordering
        self.assertContains(
            self.client.get(list_url),
            'Given 0 Family 0',
        )
        response = self.client.get(list_url + '?o=name')
        self.assertContains(response, 'Given 12 Family 12')
        self.assertContains(
            response,
            '<a class="ordering desc" href="?&o=-name"> name</a>')
        self.assertContains(
            response,
            '<a class="ordering " href="?&o=is_active"> is active</a>')

        response = self.client.get(list_url + '?o=-name')
        self.assertContains(response, 'Given 99 Family 99')
        self.assertContains(
            response,
            '<a class="ordering asc" href="?&o=name"> name</a>')
        self.assertContains(
            response,
            '<a class="ordering " href="?&o=is_active"> is active</a>')
        response = self.client.get(list_url + '?o=is_active')
        self.assertContains(response, 'Given 14 Family 14')
        self.assertNotContains(response, 'Given 12 Family 12')  # inactive
        self.assertContains(
            response,
            '<a class="ordering " href="?&o=name"> name</a>')
        self.assertContains(
            response,
            '<a class="ordering desc" href="?&o=-is_active"> is active</a>')

        # TODO multiple choice fields
        # TODO SearchForm.default


# TODO autocompletion widget tests?
