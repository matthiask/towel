import sys, os

APP_BASEDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if APP_BASEDIR not in sys.path:
    sys.path.insert(0, APP_BASEDIR)

DEBUG = True
LOCAL_DEV = False

execfile(os.path.join(APP_BASEDIR, 'secrets.py'))

CONTACT_FORM_EMAIL = [
    'mk@feinheit.ch',
    #'ll@feinheit.ch',
    ]

GOOGLE_ANALYTICS = 'UA-xxxxxxx-xx'

ADMINS = (
    ('Matthias Kestenholz', 'mk@feinheit.ch'),
    #('Livio Lunin', 'll@feinheit.ch'),
)
MANAGERS = ADMINS

TEMPLATE_DEBUG = DEBUG

TIME_ZONE = 'Europe/Zurich'
LANGUAGE_CODE = 'de-ch'
SITE_ID = 1
USE_I18N = True

MEDIA_ROOT = os.path.join(APP_BASEDIR, 'media')
MEDIA_URL = '/media/'
ADMIN_MEDIA_PREFIX = '/media/sys/admin/'

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',

    #'feinheit.middleware.ThreadLocals',
    #'feinheit.middleware.AutoTemplateFallback',
    #'feinheit.middleware.ForceDomainMiddleware',
    #'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',

    'django.middleware.locale.LocaleMiddleware',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.request',
)

ROOT_URLCONF = APP_MODULE+'.urls'

TEMPLATE_DIRS = (
    os.path.join(APP_BASEDIR, APP_MODULE, 'templates'),
    os.path.join(APP_BASEDIR, 'feinheit', 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'feinheit',
    APP_MODULE,

    #'feincms',
    #'feincms.module.medialibrary',
    #'feincms.module.page',
    #'mptt',

    #'django.contrib.comments',
)

LANGUAGES = (
    ('de', 'German'),
    ('fr', 'French'),
    ('en', 'English'),
)

FEINCMS_ADMIN_MEDIA = '/media/sys/feincms/'
TINYMCE_JS_URL = '/media/sys/feinheit/tinymce/tiny_mce.js'

#PINGING_WEBLOG_NAME = 'Nein zu neuen AKW!'
#PINGING_WEBLOG_URL = 'http://www.nein-zu-neuen-akw.ch/'

