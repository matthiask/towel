#!/bin/sh
coverage run --branch --include="*towel*" ./manage.py test testapp
