#!/bin/sh

mkdir lib
cd lib
git clone /var/cache/git/django/django.git
git clone /var/cache/git/django/feincms.git
git clone /var/cache/git/django/mptt.git
cd ..
git clone /var/cache/git/django/feinheit.git
ln -s lib/django/django django
ln -s lib/feincms/feincms feincms
ln -s lib/mptt/mptt mptt

sudo setfacl -R -d -m u:www-data:rwx media
sudo setfacl -R -m u:www-data:rwx media

cat > secrets.py << "EOD"
DATABASE_ENGINE = 'mysql'
DATABASE_HOST = 'whale.internal'
DATABASE_PORT = ''
DATABASE_NAME = 'dbname'
DATABASE_USER = 'dbname'
DATABASE_PASSWORD = 'dbpasswd'
SECRET_KEY = ''
APP_MODULE = 'co2monitor'
FORCE_DOMAIN = 'www.co2monitor.ch'

"""
CREATE DATABASE dbname DEFAULT CHARACTER SET utf8 COLLATE utf8_unicode_ci;
CREATE USER dbname@lemur.internal IDENTIFIED BY 'dbpasswd';
GRANT ALL PRIVILEGES ON dbname.* TO dbname@lemur.internal;
"""
EOD

echo "mysql -uroot -p -hwhale.internal"
