from django.contrib import admin
import models

class LogEntryAdmin(admin.ModelAdmin):
    model = models.LogEntry
    list_display = ('title','account',)

admin.site.register(models.LogEntry, LogEntryAdmin)
