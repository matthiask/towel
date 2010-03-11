from django import forms

class DateField(forms.DateField):
    def __init__(self, *args, **kwargs):
        kw = {
            'input_formats': ['%d.%m.%Y'],
            'widget': forms.DateInput(format='%d.%m.%Y'),
            }
        kw.update(kwargs)
        super(DateField, self).__init__(*args, **kw)
