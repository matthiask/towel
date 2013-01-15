from django import forms

from towel.forms import BatchForm, SearchForm
from towel.modelview import ModelView

from .models import Person, EmailAddress


class PersonBatchForm(BatchForm):
    pass

class PersonSearchForm(SearchForm):
    pass


person_views = ModelView(Person,
    search_form=PersonSearchForm,
    search_form_everywhere=True,
    batch_form=PersonBatchForm,
    paginate_by=5,
    )
