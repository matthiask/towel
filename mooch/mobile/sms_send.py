#!/usr/bin/python
#coding: utf-8
'''
Simulated SMS input from glue

@author: sr
'''
import urllib
import urllib2

HOST = 'localhost:8000'
PATH = 'mobile/reports/'

url = 'http://%s/%s' % (HOST, PATH)
print "fetching %s" % url
values = {'mobileid' : '0796151049',
          'item' : 'Some blah blah message',
          'operator' : 'swisscom' }

data = urllib.urlencode(values)
req = urllib2.Request(url, data)
response = urllib2.urlopen(req)
content = response.read()

print content
