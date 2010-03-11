from django import forms
from django.db.models import Q
from django.forms.models import inlineformset_factory
from django.utils.datastructures import MultiValueDict
from django.utils.translation import ugettext_lazy as _

from mooch import generic
from mooch.accounts.utils import Profile, access_level_required
from mooch.contacts.models import Contact
from mooch.forms import DateField
from mooch.logging.models import LogEntry
from mooch.organisation.models import Project, ProjectFile


def model_view_access_level_required(access_level):
    """
    access_level_required replacement which pops the 'profile' keyword
    argument because the ModelView cannot handle this additional argument
    (yet).
    """

    def dec(modelview, fn):
        def _fn(request, *args, **kwargs):
            kwargs.pop('profile')
            return fn(request, *args, **kwargs)
        return access_level_required(access_level)(_fn)
    return dec


class MoochModelView(generic.ModelView):
    view_decorator = model_view_access_level_required(Profile.ADMINISTRATION)


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        exclude = ('ngo', 'donated')

    start = DateField(label=_('start date'))
    end = DateField(label=_('end date'))

    def clean_budget(self):
        value = self.cleaned_data['budget']
        if  value > 10000:
            raise forms.ValidationError(
                _('Please contact us for projects over 10\'000 bucks.'))
        return value


ProjectFileInlineFormset = inlineformset_factory(Project, ProjectFile, extra=1)


import django_filters
from django.shortcuts import render_to_response
from django.template import RequestContext

class TextSearchFilter(django_filters.Filter):
    field_class = forms.CharField

    def filter(self, qs, value):
        searcher = self.model.objects.filter(
            Q(name__icontains=value)
            | Q(description__icontains=value)
            )

        # Cannot combine a unique query with a non-unique query
        if qs.query.distinct:
            return qs & searcher.distinct()
        return qs & searcher


class ProjectFilterSet(django_filters.FilterSet):
    query = TextSearchFilter()
    state = django_filters.MultipleChoiceFilter(choices=Project.STATES,
        label=_('state'), initial=['PLANNING', 'FUNDRAISING'])

    class Meta:
        model = Project
        fields = ['query', 'manager', 'state', 'start', 'end']
        order_by = ['name', 'country__name', 'manager__username', 'manager', 'state', 'start']

    def __init__(self, *args, **kwargs):
        super(ProjectFilterSet, self).__init__(*args, **kwargs)
        self.filters['start'].lookup_type = 'gte'
        self.filters['end'].lookup_type = 'lte'


class ProjectModelView(MoochModelView):
    template_object_name = 'project'

    def get_form(self, request, instance=None, **kwargs):
        return ProjectForm

    def get_formset_instances(self, request, instance=None, **kwargs):
        args = self.extend_args_if_post(request, [])
        kwargs['instance'] = instance

        return {
            'files': ProjectFileInlineFormset(*args, **kwargs),
            }

    def list_view(self, request):
        filterset = ProjectFilterSet(request.GET, queryset=self.get_query_set(request))

        data = request.GET or {}

        data_nopage = data.copy()
        if 'page' in data_nopage: del data_nopage['page']

        return render_to_response(self.get_template(request, 'filter'), {
            'filterset': filterset,
            'page': self.paginate_object_list(request, filterset.get_query_set()),
            'querystring': generic.querystring(data_nopage),
            }, context_instance=RequestContext(request))


project_view = ProjectModelView(Project)


class ProfileModelView(MoochModelView):
    def get_object(self, request, **kwargs):
        return super(ProfileModelView, self).get_object(request,
            user__username=kwargs.pop('pk'),
            **kwargs)

profile_view = ProfileModelView(Profile)


contact_view = MoochModelView(Contact)


class LogEntryModelView(MoochModelView):
    def get_form_instance(self, request, form_class, instance=None, **kwargs):
        return super(LogEntryModelView, self).get_form_instance(
            request, form_class, instance,
            initial={
                'account': request.user.get_profile().pk,
                'source': 'WEB',
            }, **kwargs)

logentry_view = LogEntryModelView(LogEntry)
