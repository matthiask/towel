import unittest
from django.test.client import Client

class SampleTest(unittest.TestCase):

    def setUp(self):
        pass

    def sms_revieve_report(self):
        client = Client()
        response = client.post("/mobile/reports/",
            {'mobileid':'0787730964', 'item':"2 Brunnen fertig gebaut!"})
        headers = response.items()
        self.assertTrue(('Content-Type', 'text/html; charset=utf-8') in headers)
        self.assertTrue(('foo','bla'))