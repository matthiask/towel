from django import forms
from django.conf.urls import patterns
from django.contrib import messages

from towel import resources
from towel.forms import SearchForm
from towel.resources.urls import resource_url_fn

from testapp.models import Resource


class ResourceSearchForm(SearchForm):
    is_active = forms.NullBooleanField(required=False)


class ResourceViewMixin(object):
    def get_queryset(self):
        return super(ResourceViewMixin, self).get_queryset().select_related(
            'user')

    def allow_delete(self, object=None, silent=True):
        if object is None:
            return True
        return self.allow_delete_if_only(object, silent=silent)

    def get_batch_actions(self):
        return super(ResourceViewMixin, self).get_batch_actions() + [
            ('set_active', 'Set active', self.set_active),
            ]

    def set_active(self, queryset):
        class SetActiveForm(forms.Form):
            is_active = forms.NullBooleanField()

        if 'confirm' in self.request.POST:
            form = SetActiveForm(self.request.POST)
            if form.is_valid():
                is_active = form.cleaned_data['is_active']
                updated = queryset.update(is_active=is_active)
                messages.success(self.request,
                    '%s have been updated.' % updated)
                return queryset

        else:
            form = SetActiveForm()

        self.template_name_suffix = '_action'
        # context = resources.ModelResourceView.get_context_data(self,
        context = self.get_context_data(
            title='Set active',
            form=form,
            action_queryset=queryset,
            action_hidden_fields=self.batch_action_hidden_fields(queryset, [
                ('batch-action', 'set_active'),
                ('confirm', 1),
                ]),
            )
        return self.render_to_response(context)


resource_url = resource_url_fn(Resource,
    mixins=(ResourceViewMixin,),
    decorators=(),
    )


urlpatterns = patterns('',
    resource_url('list', False, resources.ListView, suffix='',
        paginate_by=5,
        search_form=ResourceSearchForm,
        ),
    resource_url('detail', True, resources.DetailView, suffix=''),

    resource_url('add', False, resources.AddView),
    resource_url('edit', True, resources.EditView),
    resource_url('delete', True, resources.DeleteView),
)
