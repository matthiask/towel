from datetime import datetime

from django.db import models
from django.utils.translation import ugettext_lazy as _


from feincms.module.page.models import Page
from feincms.content.richtext.models import RichTextContent
from feincms.content.medialibrary.models import MediaFileContent
from feincms.content.raw.models import RawContent

Page.register_templates({
    'title': 'Mooch template',
    'path': 'feincms_base.html',
    'regions': (
        ('main', _('Main content area')),
        ('sidebar', _('Sidebar'), 'inherited'),
        ('moodboard', _('Moodboard'), 'inherited'),
        ),
    })

Page.register_extensions('navigation', 'titles', 'translations')
Page.create_content_type(RichTextContent, regions=('main',))
MediaFileContent.default_create_content_type(Page)

