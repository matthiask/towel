from django.http import HttpResponse
from django.utils.translation import ugettext_lazy as _


def test_view(request):
    return HttpResponse('Hello')
    