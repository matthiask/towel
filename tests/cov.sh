#!/bin/sh
coverage run --branch --include="*towel/towel*" ./manage.py test testapp
coverage html
