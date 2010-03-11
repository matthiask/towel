import unittest
from django.test.client import Client

class SampleTest(unittest.TestCase):

    def setUp(self):
        pass

    def test_shuffle(self):
        client = Client()
        status = client.get('/mobile/test')
        self.assertEqual(status, 200)