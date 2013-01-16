#!/bin/sh
coverage run --branch --include="*towel/towel*" ./manage.py test testapp
coverage html
if [ -x /usr/bin/xdg-open ] ; then /usr/bin/xdg-open htmlcov/index.html ; fi
