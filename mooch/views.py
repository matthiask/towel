from django.forms.models import inlineformset_factory

from mooch import generic
from mooch.accounts.utils import Profile, access_level_required
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

class ProjectModelView(generic.ModelView):
    template_object_name = 'project'
    view_decorator = model_view_access_level_required(Profile.ADMINISTRATION)

    def get_form(self, request, **kwargs):
        kwargs['exclude'] = ('donated', 'ngo')
        return super(ProjectModelView, self).get_form(request, **kwargs)

    def get_formset_instances(self, request, instance=None, **kwargs):
        args = []
        kwargs['instance'] = instance

        if request.method == 'POST':
            # Prepend POST and FILES to array
            args[:0] = [request.POST, request.FILES])

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
