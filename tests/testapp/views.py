from django import forms

from towel.forms import BatchForm, SearchForm
from towel.modelview import ModelView

from .models import Person, EmailAddress


class PersonBatchForm(BatchForm):
    pass


class PersonSearchForm(SearchForm):
    created__year = forms.IntegerField(required=False)


class PersonModelView(ModelView):
    pass


person_views = PersonModelView(Person,
    search_form=PersonSearchForm,
    search_form_everywhere=True,
    batch_form=PersonBatchForm,
    paginate_by=5,
    inlineformset_config={
        'emails': {'model': EmailAddress},
        },
    )
