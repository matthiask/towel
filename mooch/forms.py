from django import forms

class DateField(forms.DateField):
    def __init__(self, *args, **kwargs):
        kwargs.update({
            'input_formats': ['%d.%m.%Y'],
            'widget': forms.DateInput(format='%d.%m.%Y'),
            })
        super(DateField, self).__init__(*args, **kwargs)
