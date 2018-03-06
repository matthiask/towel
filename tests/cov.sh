#!/bin/sh
venv/bin/coverage run --branch --include="*towel/towel*" --omit="*tests*" ./manage.py test testapp
venv/bin/coverage html
