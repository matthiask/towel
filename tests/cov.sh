#!/bin/sh
coverage run --branch --include="*towel/towel*" --omit="*tests*" ./manage.py test testapp
coverage html
