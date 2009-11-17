#!/usr/bin/python

import os
import random


def shell(commands):
    for c in commands.splitlines():
        if not c:
            continue
        print c
        os.system(c)


secret_key_characters = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
sql_password_characters = 'abcdefghijklmnopqrstuvwxyz0123456789'

print 'Customer name (/var/www/<customer>/<domain>/):'
customer_name = raw_input()

print 'Domain name (/var/www/<customer>/<domain>/, without www.):'
domain_name = raw_input()

print 'Django application module (must be a valid python module name):'
module_name = raw_input()

print 'Database name and user (16 chars max, only a-z and 0-9):'
database_name = raw_input()

print 'Google Apps CNAME id [googleffffffff937e66ed]:'
google_cname = raw_input()

domain_components = 'dc=%s' % ',dc='.join(reversed(domain_name.split('.')))

dic = {
    'customer_name': customer_name,
    'database_name': database_name,
    'domain_components': domain_components,
    'domain_name': domain_name,
    'domain_id': domain_name.split('.')[0],
    'google_cname': google_cname,
    'module_name': module_name,
    'secret_key': ''.join(random.choice(secret_key_characters) for i in range(50)),
    'database_password': ''.join(random.choice(sql_password_characters) for i in range(12)),
    }


print 'Creating folders and cloning git repositories...'
shell('''mkdir lib
cd lib
git clone /var/cache/git/django/django.git
git clone /var/cache/git/django/feincms.git
git clone /var/cache/git/django/mptt.git
cd ..
git clone /var/cache/git/django/feinheit.git
ln -s lib/django/django django
ln -s lib/feincms/feincms feincms
ln -s lib/mptt/mptt mptt
''')

print 'Setting ACLs'
shell('''sudo setfacl -R -d -m u:www-data:rwx media
sudo setfacl -R -m u:www-data:rwx media
''')

print 'Setting up Django environment...'

secrets = open('secrets.py', 'w')
print >>secrets, '''DATABASE_ENGINE = 'mysql'
DATABASE_HOST = 'whale.internal'
DATABASE_PORT = ''
DATABASE_NAME = '%(database_name)s'
DATABASE_USER = '%(database_name)s'
DATABASE_PASSWORD = '%(database_password)s'
SECRET_KEY = '%(secret_key)s'
APP_MODULE = '%(module_name)s'
FORCE_%(domain_name)s = 'www.co2monitor.ch'
''' % dic
secrets.close()

print '''
Paste the following lines into an SQL prompt:
mysql -uroot -p -hwhale.internal

CREATE DATABASE %(database_name)s DEFAULT CHARACTER SET utf8 COLLATE utf8_unicode_ci;
CREATE USER %(database_name)s@lemur.internal IDENTIFIED BY '%(database_password)s';
GRANT ALL PRIVILEGES ON %(database_name)s.* TO %(database_name)s@lemur.internal;
''' % dic

print 'Renaming project folder to definitive name %(module_name)s'
shell('''git mv co2monitor %(module_name)s
git commit -m "Setup script"
''' % dic)

print 'Writing setup.ldif...'
f = open('setup.ldif', 'w')
print >>f, '# FH subdomain'
print >>f, '''dn: dc=%(domain_id)s,dc=feinheit,dc=ch,ou=domains,dc=feinheit,dc=ch
aRecord: 217.150.249.150
dc: %(domain_id)s
objectClass: dNSDomain
objectClass: top
objectClass: domainRelatedObject
associatedDomain: %(domain_id)s.feinheit.ch


''' % dic

print >>f, '# Standard DNS configuration'
print >>f, '''dn: %(domain_components)s,ou=domains,dc=feinheit,dc=ch
dc: %(domain_id)s
associatedDomain: %(domain_name)s
objectClass: dNSDomain
objectClass: domainRelatedObject
objectClass: top
nSRecord: dns1.oekohosting.ch
nSRecord: dns2.oekohosting.ch
nSRecord: dns3.oekohosting.ch
mXRecord: 1 %(domain_name)s.
sOARecord: dns1.oekohosting.ch hostmaster@feinheit.ch 0 1800 3600 604800 86400
aRecord: 217.150.249.150

dn: dc=ftp,%(domain_components)s,ou=domains,dc=feinheit,dc=ch
dc: ftp
objectClass: dNSDomain
objectClass: top
objectClass: domainRelatedObject
cNAMERecord: %(domain_name)s
associatedDomain: ftp.%(domain_name)s

dn: dc=www,%(domain_components)s,ou=domains,dc=feinheit,dc=ch
dc: www
objectClass: dNSDomain
objectClass: top
objectClass: domainRelatedObject
cNAMERecord: %(domain_name)s
associatedDomain: www.%(domain_name)s


''' % dic

print >>f, '# DNS configuration with Google Apps'
print >>f, '''dn: %(domain_components)s,ou=domains,dc=feinheit,dc=ch
dc: %(domain_id)s
associatedDomain: %(domain_name)s
objectClass: dNSDomain
objectClass: domainRelatedObject
objectClass: top
nSRecord: dns1.oekohosting.ch
nSRecord: dns2.oekohosting.ch
nSRecord: dns3.oekohosting.ch
mXRecord: 1 ASPMX.L.GOOGLE.COM.
mXRecord: 5 ALT1.ASPMX.L.GOOGLE.COM.
mXRecord: 5 ALT2.ASPMX.L.GOOGLE.COM.
mXRecord: 10 ASPMX2.GOOGLEMAIL.COM.
mXRecord: 10 ASPMX3.GOOGLEMAIL.COM.
mXRecord: 10 ASPMX4.GOOGLEMAIL.COM.
mXRecord: 10 ASPMX5.GOOGLEMAIL.COM.
sOARecord: dns1.oekohosting.ch hostmaster@feinheit.ch 0 1800 3600 604800 86400
aRecord: 217.150.249.150

dn: dc=ftp,%(domain_components)s,ou=domains,dc=feinheit,dc=ch
dc: ftp
objectClass: dNSDomain
objectClass: top
objectClass: domainRelatedObject
cNAMERecord: %(domain_name)s
associatedDomain: ftp.%(domain_name)s

dn: dc=www,%(domain_components)s,ou=domains,dc=feinheit,dc=ch
dc: www
objectClass: dNSDomain
objectClass: top
objectClass: domainRelatedObject
cNAMERecord: %(domain_name)s
associatedDomain: www.%(domain_name)s

dn: dc=kalender,%(domain_components)s,ou=domains,dc=feinheit,dc=ch
dc: kalender
cNAMERecord: ghs.google.com
objectClass: dNSDomain
objectClass: top
associatedDomain: kalender.%(domain_name)s

dn: dc=webmail,%(domain_components)s,ou=domains,dc=feinheit,dc=ch
dc: webmail
cNAMERecord: ghs.google.com
objectClass: dNSDomain
objectClass: top
associatedDomain: webmail.%(domain_name)s

dn: dc=wiki,%(domain_components)s,ou=domains,dc=feinheit,dc=ch
dc: wiki
cNAMERecord: ghs.google.com
objectClass: dNSDomain
objectClass: top
associatedDomain: wiki.%(domain_name)s

dn: dc=%(google_cname)s,%(domain_components)s,ou=domains,dc=feinheit,dc=ch
dc: %(google_cname)s
objectClass: dNSDomain
objectClass: top
objectClass: domainRelatedObject
cNAMERecord: google.com
associatedDomain: %(google_cname)s.%(domain_name)s


''' % dic


print >>f, '# Apache VHost with WSGI configuration'
print >>f, '''dn: ou=%(customer_name)s,ou=web,ou=vhosts,dc=feinheit,dc=ch
ou: %(customer_name)s
objectClass: organizationalUnit
objectClass: top

dn: ou=%(domain_name)s:80,ou=%(customer_name)s,ou=web,ou=vhosts,dc=feinheit,dc=ch
ou: %(domain_name)s:80
objectClass: organizationalUnit
objectClass: top

dn: ApacheSectionName=VirtualHost,ou=%(domain_name)s:80,ou=%(customer_name)s,ou=web,ou=vhosts,dc=feinheit,dc=ch
ApacheSectionName: VirtualHost
objectClass: ApacheSectionObj
objectClass: top
ApacheSectionArg: *:80

dn: ApacheCustomLog=/var/log/apache2/%(customer_name)s_%(domain_name)s.log combined,ApacheSectionName=VirtualHost,ou=%(domain_name)s:80,ou=%(customer_name)s,ou=web,ou=vhosts,dc=feinheit,dc=ch
objectClass: ApacheModLogConfigObj
objectClass: top
ApacheCustomLog: /var/log/apache2/%(customer_name)s_%(domain_name)s.log combined

dn: ApacheSectionName=Directory,ApacheSectionName=VirtualHost,ou=%(domain_name)s:80,ou=%(customer_name)s,ou=web,ou=vhosts,dc=feinheit,dc=ch
ApacheSectionName: Directory
ApacheSectionArg: /
objectClass: ApacheSectionObj
objectClass: top

dn: ApacheAllowOverride=All,ApacheSectionName=Directory,ApacheSectionName=VirtualHost,ou=%(domain_name)s:80,ou=%(customer_name)s,ou=web,ou=vhosts,dc=feinheit,dc=ch
ApacheAllowOverride: All
objectClass: ApacheHTAccessObj
objectClass: top

dn: ApacheServerName=%(domain_name)s,ApacheSectionName=VirtualHost,ou=%(domain_name)s:80,ou=%(customer_name)s,ou=web,ou=vhosts,dc=feinheit,dc=ch
objectClass: ApacheVirtualHostObj
objectClass: top
ApacheErrorLog: /var/log/apache2/%(customer_name)s_%(domain_name)s.log
ApacheLogLevel: Warn
ApacheServerAdmin: administrator@feinheit.ch
ApacheServerName: %(domain_name)s
ApacheServerAlias: www.%(domain_name)s
ApacheServerAlias: %(domain_id)s.feinheit.ch
ApacheDocumentRoot: /var/www/%(customer_name)s/%(domain_name)s/htdocs/
ApacheRawArg: WSGIScriptAlias / /var/www/%(customer_name)s/%(domain_name)s/runner.wsgi
ApacheRawArg: WSGIDaemonProcess %(domain_name)s user=www-data group=www-data processes=1 threads=3
ApacheRawArg: WSGIProcessGroup %(domain_name)s
ApacheRawArg: WSGIReloadMechanism Process
ApacheRawArg: Alias /favicon.ico /var/www/%(customer_name)s/%(domain_name)s/htdocs/favicon.ico
ApacheRawArg: Alias /crossdomain.xml /var/www/%(customer_name)s/%(domain_name)s/htdocs/crossdomain.xml
ApacheRawArg: Alias /media/sys/feincms /var/www/%(customer_name)s/%(domain_name)s/feincms/media/feincms
ApacheRawArg: Alias /media/sys/admin /var/www/%(customer_name)s/%(domain_name)s/django/contrib/admin/media
ApacheRawArg: Alias /media/sys/feinheit /var/www/%(customer_name)s/%(domain_name)s/feinheit/media
ApacheRawArg: Alias /media /var/www/%(customer_name)s/%(domain_name)s/media
''' % dic
f.close()


print 'Removing setup.py...'
shell('''rm setup.py''')
