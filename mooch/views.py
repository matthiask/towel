from django import forms
from django.forms.models import inlineformset_factory
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


ProjectFileInlineFormset = inlineformset_factory(Project, ProjectFile, extra=1)


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


class ProjectModelView(generic.ModelView):
    template_object_name = 'project'
    view_decorator = model_view_access_level_required(Profile.ADMINISTRATION)

    def get_form(self, request, **kwargs):
        return ProjectForm

    def get_formset_instances(self, request, instance=None, **kwargs):
        args = []
        kwargs['instance'] = instance

        if request.method == 'POST':
            # Prepend POST and FILES to array
            args[:0] = [request.POST, request.FILES]

        return {
            'files': ProjectFileInlineFormset(*args, **kwargs),
            }

project_view = ProjectModelView(Project)


class ProfileModelView(generic.ModelView):
    view_decorator = model_view_access_level_required(Profile.ADMINISTRATION)

    def get_object(self, request, **kwargs):
        return super(ProfileModelView, self).get_object(request,
            user__username=kwargs.pop('pk'),
            **kwargs)

profile_view = ProfileModelView(Profile)


class ContactModelView(generic.ModelView):
    view_decorator = model_view_access_level_required(Profile.ADMINISTRATION)

contact_view = ContactModelView(Contact)


class LogEntryModelView(generic.ModelView):
    view_decorator = model_view_access_level_required(Profile.ADMINISTRATION)

logentry_view = LogEntryModelView(LogEntry)
