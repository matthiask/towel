from __future__ import absolute_import, unicode_literals

import json

from django import forms
from django.db import models
from django.db.models import ObjectDoesNotExist
try:
    from django.forms.utils import flatatt
except ImportError:
    from django.forms.util import flatatt
from django.http import HttpResponse, QueryDict
from django.utils import six
from django.utils.encoding import force_text, force_bytes
from django.utils.functional import cached_property
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from towel import quick


class BatchForm(forms.Form):
    """
    This form class can be used to provide batch editing functionality
    in list views, similar to Django's admin actions.

    You have to implement your batch processing in the ``_context()``
    method. This method only receives one parameter, a queryset which
    is already filtered according to the selected items on the list view.
    Additionally, the current request is available as an attribute of the
    form instance, ``self.request``.

    The method ``process(self)`` may have the following return values:

    - A ``dict`` instance: Will be merged into the template context.
    - A ``HttpResponse`` instance: Will be returned directly to the client.
    - An iterable: The handler assumes successful processing of all objects
      contained in the iterable.
    - Nothing: Nothing happens.

    Usage example::

        class AddressBatchForm(BatchForm):
            subject = forms.CharField()
            body = forms.TextField()

            def process(self):
                # Form validation has already been taken care of
                subject = self.cleaned_data.get('subject')
                body = self.cleaned_data.get('body')

                if not (subject and body):
                    return {}

                sent = 0
                for item in self.batch_queryset:
                    send_mail(subject, body, settings.DEFAULT_SENDER,
                        [item.email])
                    sent += 1
                if sent:
                    messages.success(self.request, 'Sent %s emails.' % sent)

                return self.batch_queryset

        def addresses(request):
            queryset = Address.objects.all()
            batch_form = AddressBatchForm(request, queryset)
            ctx = {'addresses': queryset}

            if batch_form.should_process():
                result = form.process()
                if isinstance(result, HttpResponse):
                    return result
                elif isinstance(result, dict):
                    ctx.update(result)
                elif hasattr(result, '__iter__'):
                    messages.success(request,
                        _('Processed the following items: %s') % (
                            ', '.join(force_text(item) for item in result)))

                return HttpResponseRedirect('.')

            return render(request, 'addresses.html', ctx)

    Template code::

        {% load towel_batch_tags %}
        <form method="post" action=".">
            <ul>
            {% for address in addresses %}
                <li>
                {% batch_checkbox address.id batch_form %}
                {{ address }}
                </li>
            {% endfor %}
            </ul>

            {# Required! Otherwise, ``BatchForm.process`` does nothing. #}
            <input type="hidden" name="batchform" value="1" />

            <table>
                {{ batch_form }}
            </table>
            <button type="submit">Send mail to selected</button>
        </form>
    """

    _process = False
    ids = []

    def __init__(self, request, queryset, *args, **kwargs):
        kwargs.setdefault('prefix', 'batch')

        self.request = request
        self.queryset = queryset

        if request.method == 'POST' and 'batchform' in request.POST:
            self._process = True
            super(BatchForm, self).__init__(
                request.POST, request.FILES, *args, **kwargs)
        else:
            super(BatchForm, self).__init__(*args, **kwargs)

    def clean(self):
        """
        Cleans the batch form fields and checks whether at least one item
        had been selected.
        """
        data = super(BatchForm, self).clean()

        post_data = self.request.POST
        self.ids = [
            pk for pk in self.queryset.values_list('id', flat=True)
            if post_data.get('batch_%s' % pk)]

        if not self.ids:
            raise forms.ValidationError(_('No items selected'))

        return data

    def should_process(self):
        """
        Returns true when the submitted form was the batch form, and the
        batch form is valid.
        """
        return self._process and self.is_valid()

    @cached_property
    def batch_queryset(self):
        """
        Returns the queryset containing only items that have been selected
        for batch processing.
        """
        return self.queryset.filter(id__in=self.ids)

    def process(self):  # pragma: no cover
        """
        Actually processes the batch form submission. Override this with
        your own behavior.

        Batch forms may return the following types here (they are handled
        by ``ModelView.handle_batch_form``:

        - A ``HttpResponse``:
          Will be returned directly to the user.
        - An iterable:
          A success message will be generated containing all items in the
          iterable.
        """
        if hasattr(self, '_context'):
            import warnings
            warnings.warn(
                'The batch form \'%s.%s\' is still using \'_context\'.'
                ' Switch to using the new \'process\' method now!' % (
                    self.__class__.__module__,
                    self.__class__.__name__,
                ),
                DeprecationWarning,
            )

            ctx = self._context(self.batch_queryset)
            if 'response' in ctx:
                return ctx['response']
            return ctx

        raise NotImplementedError(
            'BatchForm.process has no default implementation.')


class SearchForm(forms.Form):
    """
    Supports persistence of searches (stores search in the session). Requires
    not only the GET parameters but the request object itself to work
    correctly.

    Usage example::

        class AddressManager(SearchManager):
            search_fields = ('first_name', 'last_name', 'address', 'email',
                'city', 'zip_code', 'created_by__email')

        class Address(models.Model):
            ...

            objects = AddressManager()

        class AddressSearchForm(SearchForm):
            orderings = {
                '': ('last_name', 'first_name'), # Default
                'dob': 'dob', # Sort by date of birth
                'random': lambda queryset: queryset.order_by('?'),
                }
            is_person = forms.NullBooleanField()

        def addresses(request):
            search_form = AddressSearchForm(request.GET, request=request)
            queryset = search_form.queryset(Address)
            ctx = {
                'addresses': queryset,
                'search_form': search_form,
                }
            return render(request, 'addresses.html', ctx)

    .. warning::

        All fields in the form need to have ``required=False`` set. Otherwise,
        form validation would already fail on the first visit on the list
        page (which would kind of defeat the purpose of a search form).

    Template code::

        <form method="get" action=".">
            <input type="hidden" name="s" value="1"> <!-- SearchForm search -->
            <table>
                {{ search_form }}
            </table>
            <button type="submit">Search</button>
        </form>

        {% for address in addresses %}
            ...
        {% endfor %}
    """

    #: Fields which are always excluded from automatic filtering
    #: in ``apply_filters``
    always_exclude = ('s', 'query', 'o')

    #: Default field values - used if not overridden by the user
    default = {}

    #: Ordering specification
    orderings = {}

    #: Quick rules, a list of (regex, mapper) tuples
    quick_rules = []

    #: Search form active?
    s = forms.CharField(required=False, widget=forms.HiddenInput(),
                        initial='1')

    #: Current ordering
    o = forms.CharField(required=False, widget=forms.HiddenInput())

    #: Full text search query
    query = forms.CharField(
        label=_('Query'),
        required=False,
        widget=forms.TextInput(attrs={'placeholder': _('Query')}))

    def __init__(self, data, *args, **kwargs):
        # Are the results filtered in any way?
        self.filtered = True
        # Is a persisted search active?
        self.persistency = False

        request = kwargs.pop('request')
        self.original_data = data
        super(SearchForm, self).__init__(
            self.prepare_data(data, request),
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
        for key, value in self.default.items():
            if key not in data:
                if hasattr(value, '__call__'):
                    value = value(request)

                if hasattr(value, '__iter__'):
                    data.setlist(key, value)
                else:
                    data[key] = value
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

        session_key = 'sf_%s.%s' % (
            self.__class__.__module__,
            self.__class__.__name__)

        if 'clear' in request.GET or 'n' in request.GET:
            if session_key in request.session:
                del request.session[session_key]

        if self.original_data and (
                set(self.original_data.keys()) & set(self.fields.keys())):
            data = self.data.copy()
            if 's' in data:
                del data['s']
                request.session[session_key] = data.urlencode()

        elif request.method == 'GET' and 's' not in request.GET:
            # try to get saved search from session
            if session_key in request.session:
                session_data = force_bytes(request.session[session_key])
                self.data = QueryDict(session_data, encoding='utf-8')
                self.persistency = True

            else:
                self.filtered = False

        elif request.method == 'POST' and 's' not in request.POST:
            # It wasn't the search form which was POSTed, hopefully :-)
            self.filtered = False

    def searching(self):
        """
        Returns ``searching`` for use as CSS class if results are filtered
        by this search form in any way.
        """

        if self.persistency or self.safe_cleaned_data.get('s'):
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

        skip = ('query', 's', 'o')

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
            if (value and hasattr(value, '__iter__')
                    and not isinstance(value, six.string_types)):
                queryset = queryset.filter(**{'%s__in' % field: value})
            elif value or value is False:
                queryset = queryset.filter(**{field: value})

        if self.quick_rules:
            quick_only = set(data.keys()) - set(self.fields.keys())
            for field in quick_only:
                if field in exclude:
                    continue

                if field.endswith('_') and (
                        field[:-1] in quick_only or field[:-1] in self.fields):
                    # Either ``quick.model_mapper`` wanted to trick us and
                    # added the model instance, too, or the quick mechanism
                    # filled an existing form field which means that the
                    # attribute has already been handled above.
                    continue

                value = data.get(field)
                if value is not None:
                    queryset = queryset.filter(**{field: value})

        return queryset

    def apply_ordering(self, queryset, ordering=None):
        """
        Applies ordering if the value in ``o`` matches a key in
        ``self.orderings``. The ordering may also be reversed,
        in which case the ``o`` value should be prefixed with
        a minus sign.
        """
        if ordering is None:
            return queryset

        if ordering and ordering[0] == '-':
            order_by, desc = ordering[1:], True
        else:
            order_by, desc = ordering, False

        if order_by not in self.orderings:
            # Ignore ordering request if unknown
            return queryset

        order_by = self.orderings[order_by]

        if hasattr(order_by, '__call__'):
            queryset = order_by(queryset)
        elif isinstance(order_by, (list, tuple)):
            queryset = queryset.order_by(*order_by)
        else:
            queryset = queryset.order_by(order_by)

        if desc:
            return queryset.reverse()
        return queryset

    def query_data(self):
        """
        Return a fulltext query and structured data which can be converted into
        simple filter() calls
        """

        if not hasattr(self, '_query_data_cache'):
            data = self.safe_cleaned_data

            if self.quick_rules:
                data, query = quick.parse_quickadd(
                    data.get('query'),
                    self.quick_rules)
                query = ' '.join(query)

                # Data in form fields overrides any quick specifications
                for k, v in self.safe_cleaned_data.items():
                    if v is not None:
                        data[k] = v
            else:
                query = data.get('query')

            self._query_data_cache = query, data
        return self._query_data_cache

    def queryset(self, model):
        """
        Return the result of the search
        """

        query, data = self.query_data()
        queryset = model.objects.search(query)
        queryset = self.apply_filters(queryset, data)
        return self.apply_ordering(queryset, data.get('o'))


class WarningsForm(forms.BaseForm):
    """
    Form subclass which allows implementing validation warnings

    In contrast to Django's ``ValidationError``, these warnings may
    be ignored by checking a checkbox.

    The warnings support consists of the following methods and properties:

    * ``WarningsForm.add_warning(<warning>)``: Adds a new warning message
    * ``WarningsForm.warnings``: A list of warnings or an empty list if there
      are none.
    * ``WarningsForm.is_valid()``: Overridden ``Form.is_valid()``
      implementation which returns ``False`` for otherwise valid forms with
      warnings, if those warnings have not been explicitly ignored (by checking
      a checkbox or by passing ``ignore_warnings=True`` to ``is_valid()``.
    * An additional form field named ``ignore_warnings`` is available - this
      field should only be displayed if ``WarningsForm.warnings`` is non-emtpy.
    """
    def __init__(self, *args, **kwargs):
        super(WarningsForm, self).__init__(*args, **kwargs)

        self.fields['ignore_warnings'] = forms.BooleanField(
            label=_('Ignore warnings'), required=False)
        self.warnings = []

    def add_warning(self, warning):
        """
        Adds a new warning, should be called while cleaning the data
        """
        self.warnings.append(warning)

    def is_valid(self, ignore_warnings=False):
        """
        ``is_valid()`` override which returns ``False`` for forms with warnings
        if these warnings haven't been explicitly ignored
        """
        if not super(WarningsForm, self).is_valid():
            return False

        if self.warnings and not (
                ignore_warnings or self.cleaned_data.get('ignore_warnings')):
            return False

        return True


class StrippedInputMixin(object):
    def value_from_datadict(self, data, files, name):
        value = data.get(name, None)
        if isinstance(value, six.string_types):
            return value.strip()
        return value


class StrippedTextInput(StrippedInputMixin, forms.TextInput):
    """
    ``TextInput`` form widget subclass returning stripped contents only
    """
    pass


class StrippedTextarea(StrippedInputMixin, forms.Textarea):
    """
    ``Textarea`` form widget subclass returning stripped contents only
    """
    pass


def towel_formfield_callback(field, **kwargs):
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


#: Backwards compatibility, provide the function under the old name
#: ``stripped_formfield_callback`` too.
def stripped_formfield_callback(field, **kwargs):
    import warnings
    warnings.warn(
        'stripped_formfield_callback has been renamed to'
        ' towel_formfield_callback, please start using the new name.',
        DeprecationWarning, stacklevel=2)
    return towel_formfield_callback(field, **kwargs)


def autocompletion_response(queryset, limit=10):
    """
    Helper which returns a ``HttpResponse`` list of instances in a format
    suitable for consumption by jQuery UI Autocomplete, respectively
    ``towel.forms.ModelAutocompleteWidget``.
    """
    return HttpResponse(
        json.dumps([
            {
                'label': force_text(instance),
                'value': instance.pk,
            } for instance in queryset[:limit]
        ]),
        content_type='application/json',
    )


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
        assert (url is None) != (queryset is None), (
            'Provide either url or queryset')

        self.url = url
        self.queryset = queryset
        super(ModelAutocompleteWidget, self).__init__(attrs)

    def render(self, name, value, attrs=None, choices=()):
        if value is None:
            value = ''
        final_attrs = self.build_attrs(attrs, type='hidden', name=name)
        if value != '':
            # Only add the 'value' attribute if a value is non-empty.
            final_attrs['value'] = force_text(self._format_value(value))

        hidden = '<input%s />' % flatatt(final_attrs)

        final_attrs['type'] = 'text'
        final_attrs['id'] += '_ac'
        del final_attrs['name']

        try:
            instance = self.choices.queryset.get(pk=value)
            final_attrs['value'] = force_text(instance)
        except (ObjectDoesNotExist, ValueError, TypeError):
            final_attrs['value'] = ''

        if self.is_required:
            ac = '<input%s />' % flatatt(final_attrs)
        else:
            final_attrs.setdefault('class', '')
            final_attrs['class'] += ' ac_nullable'

            ac = (
                ' <a href="#" id="%(id)s_cl" class="ac_clear">'
                ' %(text)s</a>' % {
                    'id': final_attrs['id'][:-3],
                    'text': _('clear'),
                }
            ) + ('<input%s />' % flatatt(final_attrs))

        js = '''<script type="text/javascript">
$(function() {
    $('#%(id)s_ac').autocomplete({
        source: %(source)s,
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
                return '\'%s\'' % self.url()
            return '\'%s\'' % self.url
        else:
            data = json.dumps([
                {
                    'label': force_text(o),
                    'value': o.id,
                } for o in self.queryset.all()
            ])

            return '''function (request, response) {
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
    """
    You should probably use harvest chosen instead.
    """
    def __init__(self, attrs=None, queryset=None):
        self.queryset = queryset
        super(MultipleAutocompletionWidget, self).__init__(attrs)

    def _possible(self):
        return dict((force_text(o).lower(), o) for o in self.queryset._clone())

    def render(self, name, value, attrs=None, choices=()):
        if value is None:
            value = []
        final_attrs = self.build_attrs(attrs, name=name, type='text')

        if value:
            value = ', '.join(
                force_text(o) for o in self.queryset.filter(id__in=value))

        js = '''<script type="text/javascript">
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
''' % {
            'id': final_attrs.get('id', name),
            'name': name,
            'source': self._source(),
        }

        return mark_safe(
            '<textarea%s>%s</textarea>' % (
                flatatt(final_attrs),
                value,
            ) + js
        )

    def value_from_datadict(self, data, files, name):
        value = data.get(name, None)
        if not value:
            return []

        possible = self._possible()
        values = [
            s for s in
            [s.strip() for s in value.lower().split(',')]
            if s]
        return list(set(possible.get(s, InvalidEntry).pk for s in values))

    def _source(self):
        return '''function(request, response) {
    response($.ui.autocomplete.filter(%(data)s, extractLast(request.term)));
    }''' % {
            'data': json.dumps(
                [force_text(o) for o in self.queryset._clone()]),
        }
