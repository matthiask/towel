#coding: utf-8

from django.http import HttpResponse
from django import forms
from django.template import Template
from django.template.context import Context

class ShortMessage(forms.Form):
    mobileid = forms.IntegerField()
    message = forms.CharField(max_length=160, min_length=0)
    
def render_string_to_response(str):
    template = Template("{{ object }}")
    context = Context({"object": str})
    return template.render(context)

def sms_charge(request, message, amount):
    """
    Returns a message and charges the user a specific value.
    Charge amount is in Swiss centimes (Rappen) (uint)
    """  
    msg = render_string_to_response(message)
    response = HttpResponse(msg,'text/plain')
    response['X-CHARGE'] = amount
    return response

def test_view(request):
    return sms_charge(request, 'Hello', 200)
    
def receive_donation(request):
    return sms_charge(request, u'Vielen Dank für ihre Unterstützung!', 20)

def receive_report(request):
    return sms_charge(request, u'Report erhalten und in Projekt gespeichert', 20)
    