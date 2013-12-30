#!/bin/sh

(
    cd .tox/py27-django17
    bin/pip install -U --editable=git+git://github.com/django/django.git@master#egg=django-dev
)
(
    cd .tox/py32-django17
    bin/pip install -U --editable=git+git://github.com/django/django.git@master#egg=django-dev
)
(
    cd .tox/py33-django17
    bin/pip install -U --editable=git+git://github.com/django/django.git@master#egg=django-dev
)
