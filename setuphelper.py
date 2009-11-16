#!/usr/bin/python

import os
import random

secret_key_characters = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
sql_password_characters = 'abcdefghijklmnopqrstuvwxyz0123456789'

print 'Please enter the name of the Django application module'
module_name = raw_input()

print 'Please enter the database name and user'
database_name = raw_input()

dic = {
    'database_name': database_name,
    'module_name': module_name,
    'secret_key': ''.join(random.choice(secret_key_characters) for i in range(50)),
    'database_password': ''.join(random.choice(sql_password_characters) for i in range(12)),
    }

secrets = open('secrets.py', 'w')
print >>secrets, '''DATABASE_ENGINE = 'mysql'
DATABASE_HOST = 'whale.internal'
DATABASE_PORT = ''
DATABASE_NAME = '%(database_name)s'
DATABASE_USER = '%(database_name)s'
DATABASE_PASSWORD = '%(database_password)s'
SECRET_KEY = '%(secret_key)s'
APP_MODULE = '%(module_name)s'
FORCE_DOMAIN = 'www.co2monitor.ch'
''' % dic

print '''
Paste the following lines into an SQL prompt:

CREATE DATABASE %(database_name)s DEFAULT CHARACTER SET utf8 COLLATE utf8_unicode_ci;
CREATE USER %(database_name)s@lemur.internal IDENTIFIED BY '%(database_password)s';
GRANT ALL PRIVILEGES ON %(database_name)s.* TO %(database_name)s@lemur.internal;
''' % dic

print 'Renaming project folder to definitive name %(module_name)s'
os.system('git mv co2monitor %(module_name)s' % dic)
os.system('git commit -m "Setup script"')
