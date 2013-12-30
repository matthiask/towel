from __future__ import absolute_import, unicode_literals

import re

from django import forms
from django.contrib import messages
from django.shortcuts import redirect

from towel import quick
from towel.forms import BatchForm, SearchForm, WarningsForm
from towel.modelview import ModelView

from .models import Person, EmailAddress, Message


class PersonBatchForm(BatchForm):
    is_active = forms.NullBooleanField()

    def process(self):
        if self.cleaned_data.get('is_active') is not None:
            updated = self.batch_queryset.update(
                is_active=self.cleaned_data['is_active'])
            messages.success(self.request, '%s have been updated.' % updated)

        return self.batch_queryset


class PersonSearchForm(SearchForm):
    orderings = {
        'name': ('family_name', 'given_name'),
        'is_active': ('-is_active', 'family_name'),
    }

    quick_rules = [
        (re.compile(r'^is:active$'),
            quick.static(is_active=True)),
        (re.compile(r'^is:inactive$'),
            quick.static(is_active=False)),
        (re.compile(r'^active:(?P<bool>\w+)$'),
            quick.bool_mapper('is_active')),
        (re.compile(r'^year:(?P<year>\d{4})$'),
            lambda values: {'created__year': values['year']}),
    ]
    created__year = forms.IntegerField(required=False)
    is_active = forms.NullBooleanField(required=False)


class PersonForm(forms.ModelForm):
    class Meta:
        model = Person
        fields = ('family_name', 'given_name')


class MessageForm(forms.ModelForm, WarningsForm):
    class Meta:
        model = Message

    def __init__(self, *args, **kwargs):
        person = kwargs.pop('person')
        super(MessageForm, self).__init__(*args, **kwargs)
        self.fields['sent_to'].queryset = person.emailaddress_set.all()

    def clean(self):
        data = super(MessageForm, self).clean()

        if not data.get('message', '').strip():
            self.add_warning('Only spaces in message, really send?')

        return data


class PersonModelView(ModelView):
    def additional_urls(self):
        return (
            (r'^%(detail)s/message/$', self.message),
        )

    def deletion_allowed(self, request, instance):
        return self.deletion_allowed_if_only(request, instance, [Person])

    def save_formsets(self, request, form, formsets, change):
        self.save_formset_deletion_allowed_if_only(
            request, form, formsets['emails'], change, [EmailAddress])

    def message(self, request, *args, **kwargs):
        instance = self.get_object_or_404(request, *args, **kwargs)

        if request.method == 'POST':
            form = MessageForm(request.POST, person=instance)

            if form.is_valid():
                form.save()
                return redirect(instance)

        else:
            form = MessageForm(person=instance)

        return self.render(
            request,
            self.get_template(request, 'form'),
            self.get_context(request, {
                self.template_object_name: instance,
                'form': form,
            }),
        )


person_views = PersonModelView(
    Person,
    search_form=PersonSearchForm,
    search_form_everywhere=True,
    batch_form=PersonBatchForm,
    form_class=PersonForm,
    paginate_by=5,
    inlineformset_config={
        'emails': {'model': EmailAddress},
    },
)


class EmailAddressSearchForm(SearchForm):
    default = {
        'person__is_active': True,
        'person__relationship': ('', 'single'),
    }
    person__is_active = forms.NullBooleanField(required=False)
    person__relationship = forms.MultipleChoiceField(
        required=False, choices=Person.RELATIONSHIP_CHOICES)


emailaddress_views = ModelView(
    EmailAddress,
    paginate_by=5,
    search_form=EmailAddressSearchForm,
)


message_views = ModelView(
    Message,
    paginate_by=5,
)
