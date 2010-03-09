# coding: utf-8
import os
from django.http import HttpResponse
#from django.utils import simplejson
from django.conf import settings
from django.core import serializers
from django.template import RequestContext
from django.http import Http404
from django.template.loader import render_to_string
from django.shortcuts import render_to_response, get_object_or_404
from django.views.generic.simple import direct_to_template as render
from django.http import HttpResponseRedirect
from django.views.generic import list_detail
from django import forms
from django.utils.translation import ugettext_lazy as _
from django.contrib import messages

from models import Project, ProjectFile, get_current_ngo
from mooch.accounts.middleware import get_current_user
from mooch.accounts.utils import Profile, access_level_required


@access_level_required(Profile.ADMINISTRATION)
def project_list(request, profile):
    object_list = Project.objects.all()
    return render(request, 'organisation/project_list.html', locals())


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        exclude = ('ngo', 'donated')

    start = forms.DateField(input_formats=['%d.%m.%Y'],
                            widget=forms.DateInput(format='%d.%m.%Y'))
    end = forms.DateField(input_formats=['%d.%m.%Y'],
                          widget=forms.DateInput(format='%d.%m.%Y'))

    def clean_budget(self):
        value = self.cleaned_data['budget']
        if  value > 10000:
            raise forms.ValidationError(
                _('Please contact us for projects over 10\'000 bucks.'))
        return value


@access_level_required(Profile.ADMINISTRATION)
def project_detail(request, object_id, profile):
    return list_detail.object_detail(request,
        queryset=Project.objects.all(),
        object_id=object_id,
        template_object_name='project',
    )


@access_level_required(Profile.ADMINISTRATION)
def project_new(request, profile):
    if request.method=='POST':
        form = ProjectForm(request.POST)

        if form.is_valid():
            project = form.save()
            messages.success(request, _('The project has been created.'))
            return HttpResponseRedirect('../%s/' % project.pk)
    else:
        data = {
            'ngo': profile.ngo.id,
            'manager': profile.user,
            'donated': 0.0,
            'name': 'New Project Name',
            'description': 'Type some shit in here',
        }

        form = ProjectForm(initial=data)

    return render(request, 'organisation/project_form.html', { 'form':form})


@access_level_required(Profile.ADMINISTRATION)
def project_edit(request, object_id, profile):
    project = get_object_or_404(Project.objects.all(), pk=object_id)

    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)

        if form.is_valid():
            form.save()
            messages.success(request, _('The project has been updated!'))
            return HttpResponseRedirect(project.get_absolute_url())
    else:
        form = ProjectForm(instance=project)

    return render(request, 'organisation/project_form.html', locals())


@access_level_required(Profile.ADMINISTRATION)
def project_delete(request, object_id, profile):
    project = get_object_or_404(Project,id=object_id)
    project.delete()
    request.user.message_set.create(message='%s was deleted.' % project.name )
    return HttpResponseRedirect("/projects/list/")


@access_level_required(Profile.ADMINISTRATION)
def project_add_file(request, object_id, profile):
    project = get_object_or_404(Project.objects.all(), pk=object_id)

    if request.method == 'POST':
        file = request.FILES['userfile']
        path = os.path.join('uploads', 'projects', project.name.lower(), 'files')

        save_uploaded_file(file, os.path.join(settings.MEDIA_ROOT, path))

        project_file = ProjectFile.objects.get_or_create(
            project=project, file = os.path.join(path, file.name) )

    files = project.files.all()
    return render(request, 'organisation/project_files.html', locals())


@access_level_required(Profile.ADMINISTRATION)
def project_delete_file(request, object_id, profile):
    file = get_object_or_404(ProjectFile.objects.all(), pk=object_id)
    project = file.project
    file.delete()
    files = ProjectFile.objects.filter(project=project)
    return render(request, 'organisation/project_files.html', locals())


def save_uploaded_file(file, path):
    if not os.path.isdir(path):
        os.makedirs(path)
    destination = open(os.path.join(path, file.name), 'wb+')
    for chunk in file.chunks():
        destination.write(chunk)
    os.chmod(os.path.join(path, file.name), 0664)
    destination.close()

