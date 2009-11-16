#!/bin/sh

echo "Creating folders and cloning git repositories..."
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

echo "Setting ACLs..."
sudo setfacl -R -d -m u:www-data:rwx media
sudo setfacl -R -m u:www-data:rwx media

echo "Setting up Django environment..."
python setuphelper.py

echo "Copy-paste the following command to open a MySQL connection"
echo "mysql -uroot -p -hwhale.internal"

echo "You should remove setup.sh and setuphelper.py now"
echo "rm setup.sh setuphelper.py"
