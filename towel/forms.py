import pickle

from django import forms
from django.db import models
from django.forms.util import flatatt
from django.utils import simplejson
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _


class BatchForm(forms.Form):
    ids = []
    process = False

    def __init__(self, request, *args, **kwargs):
        kwargs.setdefault('prefix', 'batch')

        self.request = request

        if request.method == 'POST' and 'batchform' in request.POST:
            self.process = True
            super(BatchForm, self).__init__(request.POST, *args, **kwargs)
        else:
            super(BatchForm, self).__init__(*args, **kwargs)

    def context(self, queryset):
        ctx = {
            'batch_form': self,
            }

        if self.process and self.is_valid():
            ctx.update(self._context(
                self.selected_items(self.request.POST, queryset)))

        return ctx

    def _context(self, batch_queryset):
        raise NotImplementedError

    def selected_items(self, post_data, queryset):
        self.ids = queryset.values_list('id', flat=True)
        self.ids = [pk for pk in self.ids if post_data.get('batch_%s' % pk)]
        return queryset.filter(id__in=self.ids)


class SearchForm(forms.Form):
    always_exclude = ('s', 'query')
    default = {}

    # search form active?
    s = forms.CharField(required=False)
    query = forms.CharField(required=False, label=_('Query'))

    def __init__(self, data, *args, **kwargs):
        request = kwargs.pop('request')
        super(SearchForm, self).__init__(self.prepare_data(data, request),
            *args, **kwargs)
        self.persist(request)
        self.post_init(request)

    def prepare_data(self, data, request):
        if not self.default:
            return data

        data = data.copy()
        for k, v in self.default.items():
            if k not in data:
                if hasattr(v, '__call__'):
                    v = v(request)

                if hasattr(v, '__iter__'):
                    data.setlist(k, v)
                else:
                    data[k] = v
        return data

    def post_init(self, request):
        # Hook for customizations
        pass

    def persist(self, request):
        session_key = '_'.join(('sf', self.__class__.__name__, request.path))

        if 'clear' in request.GET or 'n' in request.GET:
            if session_key in request.session:
                del request.session[session_key]

        if request.method == 'GET' and 's' not in request.GET:
            # try to get saved search from session
            if session_key in request.session:
                self.data = pickle.loads(request.session[session_key])
                self.persistency = True
        else:
            request.session[session_key] = pickle.dumps(self.data)

    def searching(self):
        if hasattr(self, 'persistency') or self.safe_cleaned_data.get('s'):
            return 'searching'
        return ''

    @property
    def safe_cleaned_data(self):
        self.is_valid()
        try:
            return self.cleaned_data.copy()
        except AttributeError:
            return {}

    def fields_iterator(self):
        skip = ('query', 's')

        for field in self:
            if field.name not in skip:
                yield field

    def apply_filters(self, queryset, data, exclude=()):
        exclude = list(exclude) + list(self.always_exclude)

        for field in self.fields.keys():
            if field in exclude:
                continue

            value = data.get(field)
            if hasattr(value, '__iter__') and value:
                queryset = queryset.filter(**{'%s__in' % field: value})
            elif value or value is False:
                queryset = queryset.filter(**{field: value})

        return queryset

    def queryset(self, model):
        data = self.safe_cleaned_data
        queryset = model.objects.search(data.get('query'))
        return self.apply_filters(queryset, data)


class StrippedTextInput(forms.TextInput):
    def value_from_datadict(self, data, files, name):
        value = data.get(name, None)
        if isinstance(value, (str, unicode)):
            return value.strip()
        return value

    def render(self, *args, **kwargs):
        return super(StrippedTextInput, self).render(*args, **kwargs)


class StrippedTextarea(forms.Textarea):
    def value_from_datadict(self, data, files, name):
        value = data.get(name, None)
        if isinstance(value, (str, unicode)):
            return value.strip()
        return value

    def render(self, *args, **kwargs):
        return super(StrippedTextarea, self).render(*args, **kwargs)


def stripped_formfield_callback(field, **kwargs):
    if isinstance(field, models.CharField) and not field.choices:
        kwargs['widget'] = StrippedTextInput()
    elif isinstance(field, models.TextField):
        kwargs['widget'] = StrippedTextarea()
    elif isinstance(field, models.DateTimeField):
        kwargs['widget'] = forms.DateTimeInput(attrs={'class': 'dateinput'})
    elif isinstance(field, models.DateField):
        kwargs['widget'] = forms.DateInput(attrs={'class': 'dateinput'})

    return field.formfield(**kwargs)


class ModelAutocompleteWidget(forms.TextInput):
    def __init__(self, attrs=None, url=None, queryset=None):
        assert url or queryset, 'Provide either url or queryset'

        self.url = url
        self.queryset = queryset
        super(ModelAutocompleteWidget, self).__init__(attrs)

    def render(self, name, value, attrs=None, choices=()):
        if value is None:
            value = ''
        final_attrs = self.build_attrs(attrs, type='hidden', name=name)
        if value != '':
            # Only add the 'value' attribute if a value is non-empty.
            final_attrs['value'] = force_unicode(self._format_value(value))

        hidden = u'<input%s />' % flatatt(final_attrs)

        final_attrs['type'] = 'text'
        final_attrs['name'] += '_ac'
        final_attrs['id'] += '_ac'

        try:
            model = self.choices.queryset.get(pk=value)
            final_attrs['value'] = force_unicode(model)
        except (self.choices.queryset.model.DoesNotExist, ValueError, TypeError):
            final_attrs['value'] = u''

        if self.is_required:
            ac = u'<input%s />' % flatatt(final_attrs)
        else:
            final_attrs['class'] = final_attrs.get('class', '') + ' ac_nullable'

            ac = (u' <a href="#" id="%(id)s_cl" class="ac_clear"> %(text)s</a>' % {
                'id': final_attrs['id'][:-3],
                'text': _('clear'),
                }) + (u'<input%s />' % flatatt(final_attrs))

        js = '''<script type="text/javascript">
$(function() {
    $('#%(id)s_ac').autocomplete(%(source)s, {
        matchContains: true, minChars: 2, max: 100
    }).result(function(event, item) {
        $('#%(id)s').val(item[1]).trigger('change');
    }).bind('focus', function() {
        this.select();
    }).bind('blur', function() {
        if (!this.value)
            $('#%(id)s').val('');
    });
    $('#%(id)s_cl').click(function(){
        $('#%(id)s, #%(id)s_ac').val('');
    });
});
</script>
''' % {'id': attrs.get('id', name), 'name': name, 'source': self._source()}

        return mark_safe(hidden + ac + js)

    def _source(self):
        if self.url:
            return u'\'%s\'' % self.url
        else:
            return simplejson.dumps([(unicode(o), o.id) for o in self.queryset.all()])
