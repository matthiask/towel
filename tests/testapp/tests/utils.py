from django.test import TestCase

from towel.utils import related_classes, safe_queryset_and, tryreverse

from testapp.models import Person, EmailAddress


class UtilsTest(TestCase):
    def test_related_classes(self):
        """Test the functionality of towel.utils.related_classes"""
        person = Person.objects.create(
            family_name='Muster',
            given_name='Hans',
            )
        EmailAddress.objects.create(
            person=person,
            email='hans@example.com',
            )

        self.assertEqual(
            set(related_classes(person)),
            set((Person, EmailAddress)),
            )

    def test_safe_queryset_and(self):
        def _transform_nothing(queryset):
            pass

        qs1 = EmailAddress.objects.search('blub').transform(
            _transform_nothing).select_related()
        qs2 = EmailAddress.objects.distinct().reverse().select_related(
            'person')
        qs3 = EmailAddress.objects.all()

        qs = safe_queryset_and(safe_queryset_and(qs1, qs2), qs3)

        self.assertEqual(qs._transform_fns, [_transform_nothing])
        self.assertFalse(qs.query.standard_ordering)
        self.assertEqual(qs.query.select_related, {'person': {}})
        self.assertTrue(qs.query.distinct)

        qs = safe_queryset_and(
            EmailAddress.objects.select_related(),
            EmailAddress.objects.select_related(),
            )

        self.assertTrue(qs.query.select_related)
        self.assertFalse(qs.query.distinct)

        qs = safe_queryset_and(
            EmailAddress.objects.all(),
            EmailAddress.objects.select_related(),
            )

        self.assertTrue(qs.query.select_related)

    def test_tryreverse(self):
        self.assertEqual(tryreverse('asdf42'), None)
        self.assertEqual(tryreverse('admin:index'), '/admin/')
