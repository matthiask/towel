import pickle

from django import forms
from django.db import models
from django.forms.util import flatatt
from django.utils import simplejson
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _


class BatchForm(forms.Form):
    """Batch form"""

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
    """
    Search form

    Supports persistence of searches (stores search in the session). Requires
    not only the GET parameters but the request object itself to work
    correctly.
    """

    #: Fields which are always excluded from automatic filtering
    #: in ``apply_filters``
    always_exclude = ('s', 'query')

    #: Default field values - used if not overridden by the user
    default = {}

    # search form active?
    s = forms.CharField(required=False)
    query = forms.CharField(required=False, label=_('Query'))

    def __init__(self, data, *args, **kwargs):
        request = kwargs.pop('request')
        self.original_data = data
        super(SearchForm, self).__init__(self.prepare_data(data, request),
            *args, **kwargs)
        self.persist(request)
        self.post_init(request)

    def prepare_data(self, data, request):
        """
        Fill in default values from ``default`` if they aren't provided by
        the user.
        """

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
        """
        Hook for customizations.
        """

        pass

    def persist(self, request):
        """
        Persist the search in the session, or load saved search if user
        isn't searching right now.
        """

        session_key = '_'.join(('sf', self.__class__.__name__, request.path))

        if 'clear' in request.GET or 'n' in request.GET:
            if session_key in request.session:
                del request.session[session_key]

        if self.original_data:
            data = self.data.copy()
            if 's' in data:
                del data['s']
                request.session[session_key] = pickle.dumps(data)

        elif request.method == 'GET' and 's' not in request.GET:
            # try to get saved search from session
            if session_key in request.session:
                self.data = pickle.loads(request.session[session_key])
                self.persistency = True

    def searching(self):
        """
        Returns ``searching`` for use as CSS class if results are filtered
        by this search form in any way.
        """

        if hasattr(self, 'persistency') or self.safe_cleaned_data.get('s'):
            return 'searching'
        return ''

    @property
    def safe_cleaned_data(self):
        """
        Safely return a dictionary of values, even if search form isn't valid.
        """

        self.is_valid()
        try:
            return self.cleaned_data.copy()
        except AttributeError:
            return {}

    def fields_iterator(self):
        """
        Yield all additional search fields.
        """

        skip = ('query', 's')

        for field in self:
            if field.name not in skip:
                yield field

    def apply_filters(self, queryset, data, exclude=()):
        """
        Automatically apply filters

        Uses form field names for ``filter()`` argument construction.
        """

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
        """
        Return the result of the search
        """

        data = self.safe_cleaned_data
        queryset = model.objects.search(data.get('query'))
        return self.apply_filters(queryset, data)


class StrippedTextInput(forms.TextInput):
    """
    ``TextInput`` form widget subclass returning stripped contents only
    """

    def value_from_datadict(self, data, files, name):
        value = data.get(name, None)
        if isinstance(value, (str, unicode)):
            return value.strip()
        return value

    def render(self, *args, **kwargs):
        return super(StrippedTextInput, self).render(*args, **kwargs)


class StrippedTextarea(forms.Textarea):
    """
    ``Textarea`` form widget subclass returning stripped contents only
    """

    def value_from_datadict(self, data, files, name):
        value = data.get(name, None)
        if isinstance(value, (str, unicode)):
            return value.strip()
        return value

    def render(self, *args, **kwargs):
        return super(StrippedTextarea, self).render(*args, **kwargs)


def stripped_formfield_callback(field, **kwargs):
    """
    Use this callback as ``formfield_callback`` if you want to use stripped
    text inputs and textareas automatically without manually specifying the
    widgets. Adds a ``dateinput`` class to date and datetime fields too.
    """

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
    """
    Model autocompletion widget using jQuery UI Autocomplete

    Supports both querysets and JSON-returning AJAX handlers as data
    sources. Use as follows::

        class MyForm(forms.ModelForm):
            customer = forms.ModelChoiceField(Customer.objects.all(),
                widget=ModelAutocompleteWidget(url='/customers/search_ajax/'),
                )
            type = forms.ModelChoiceField(Type.objects.all(),
                widget=ModelAutocompleteWidget(queryset=Type.objects.all()),
                )

    You need to make sure that the jQuery UI files are loaded correctly
    yourself.
    """

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

        js = u'''<script type="text/javascript">
$(function() {
    $('#%(id)s_ac').autocomplete({
        source: %(source)s,
        minLength: 2,
        focus: function(event, ui) {
            $('#%(id)s_ac').val(ui.item.label);
            return false;
        },
        select: function(event, ui) {
            $('#%(id)s').val(ui.item.value).trigger('change');
            $('#%(id)s_ac').val(ui.item.label);
            return false;
        }
    }).bind('focus', function() {
        this.select();
    }).bind('blur', function() {
        if (!this.value)
            $('#%(id)s').val('');
    });
    $('#%(id)s_cl').click(function(){
        $('#%(id)s, #%(id)s_ac').val('');
        return false;
    });
});
</script>
''' % {'id': attrs.get('id', name), 'name': name, 'source': self._source()}

        return mark_safe(hidden + ac + js)

    def _source(self):
        if self.url:
            if hasattr(self.url, '__call__'):
                return u'\'%s\'' % self.url()
            return u'\'%s\'' % self.url
        else:
            data = simplejson.dumps([{
                'label': unicode(o),
                'value': o.id,
                } for o in self.queryset.all()])

            return u'''function (request, response) {
    var data = %(data)s, ret = [], term = request.term.toLowerCase();
    for (var i=0; i<data.length; ++i) {
        if (data[i].label.toLowerCase().indexOf(term) != -1)
            ret.push(data[i]);
    }
    response(ret);
}
''' % {'data': data}


class InvalidEntry(object):
    pk = None

class MultipleAutocompletionWidget(forms.TextInput):
    def __init__(self, attrs=None, queryset=None):
        self.queryset = queryset
        super(MultipleAutocompletionWidget, self).__init__(attrs)

    def _possible(self):
        return dict((unicode(o).lower(), o) for o in self.queryset._clone())

    def render(self, name, value, attrs=None, choices=()):
        if value is None: value = []
        final_attrs = self.build_attrs(attrs, name=name, type='text')

        if value:
            value = u', '.join(unicode(o) for o in
                self.queryset.filter(id__in=value))

        js = u'''<script type="text/javascript">
$(function() {
    function split( val ) {
        return val.split( /,\s*/ );
    }
    function extractLast( term ) {
        return split( term ).pop();
    }

    $( "#%(id)s" )
        // don't navigate away from the field on tab when selecting an item
        .bind( "keydown", function( event ) {
            if ( event.keyCode === $.ui.keyCode.TAB &&
                    $( this ).data( "autocomplete" ).menu.active ) {
                event.preventDefault();
            }
        })
        .autocomplete({
            source: %(source)s,
            search: function() {
                // custom minLength
                var term = extractLast( this.value );
                if ( term.length < 2 ) {
                    return false;
                }
            },
            focus: function() {
                // prevent value inserted on focus
                return false;
            },
            select: function( event, ui ) {
                var terms = split( this.value );
                // remove the current input
                terms.pop();
                // add the selected item
                terms.push( ui.item.value );
                // add placeholder to get the comma-and-space at the end
                terms.push( "" );
                this.value = terms.join( ", " );
                return false;
            }
    });
});
</script>
''' % {'id': final_attrs.get('id', name), 'name': name, 'source': self._source()}

        return mark_safe(u'<textarea%s>%s</textarea>' % (flatatt(final_attrs), value) + js)

    def value_from_datadict(self, data, files, name):
        value = data.get(name, None)
        if not value:
            return []

        possible = self._possible()
        values = [s for s in [s.strip() for s in value.lower().split(',')] if s]
        return list(set(possible.get(s, InvalidEntry).pk for s in values))

    def _source(self):
        return u'''function(request, response) {
            response($.ui.autocomplete.filter(%(data)s, extractLast(request.term))); }''' % {
                'data': simplejson.dumps([unicode(o) for o in self.queryset._clone()]),
                }
