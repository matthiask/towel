from django.contrib import admin
import models

class LogEntryAdmin(admin.ModelAdmin):
    model = models.LogEntry
    list_display = ('account', 'title')

#admin.site.register(models.Project, ProjectAdmin)
