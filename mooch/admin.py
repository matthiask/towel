from django.contrib import admin

from models import *
from organisation.models import NGO, Project

admin.site.register(NGO)
admin.site.register(Project)


"""
class TemplateOptions(admin.ModelAdmin):
    list_display = ('name')

admin.site.register(Template, TemplateOptions)
"""
