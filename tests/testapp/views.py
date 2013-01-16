from django import forms

from towel.forms import BatchForm, SearchForm, towel_formfield_callback
from towel.modelview import ModelView

from .models import Person, EmailAddress


class PersonBatchForm(BatchForm):
    pass


class PersonSearchForm(SearchForm):
    created__year = forms.IntegerField(required=False)


class PersonForm(forms.ModelForm):
    class Meta:
        model = Person
        fields = ('family_name', 'given_name')


class PersonModelView(ModelView):
    def get_formfield_callback(self, request):
        return towel_formfield_callback

    def deletion_allowed(self, request, instance):
        return self.deletion_allowed_if_only(request, instance, [Person])

    def save_formsets(self, request, form, formsets, change):
        self.save_formset_deletion_allowed_if_only(request, form,
            formsets['emails'], change, [EmailAddress])


person_views = PersonModelView(Person,
    search_form=PersonSearchForm,
    search_form_everywhere=True,
    batch_form=PersonBatchForm,
    form_class=PersonForm,
    paginate_by=5,
    inlineformset_config={
        'emails': {'model': EmailAddress},
        },
    )
