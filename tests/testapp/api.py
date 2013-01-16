from django.views.decorators.csrf import csrf_exempt

from towel.api import API

from .models import Person, EmailAddress, Message


api_v1 = API('v1', decorators=[
    csrf_exempt,
    ])

api_v1.register(Person)
api_v1.register(EmailAddress)
api_v1.register(Message)
