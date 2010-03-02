from django.contrib import admin
from mooch.organisation import models

class ProjectFileInline(admin.StackedInline):
    model = models.ProjectFile

class ProjectAdmin(admin.ModelAdmin):
    model = models.Project
    inlines = (ProjectFileInline,)

admin.site.register(models.NGO)
admin.site.register(models.Project, ProjectAdmin)
