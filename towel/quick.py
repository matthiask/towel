"""
This module beefs up the default full text search field to be a little
bit more versatile. It allows specifying patterns such as ``is:unread``
or ``!important`` which are extracted from the query string and returned
as standalone values allowing the implementation of a search syntax
known from f.e. Google Mail.

Quick rules always consist of two parts: A regular expression pulling
values out of the query string and a mapper which maps the values from
the regex to something else which may be directly usable by forms.

Usage example::

    QUICK_RULES = [
        (re.compile(r'!!'), quick.static(important=True)),
        (re.compile(r'@(?P<username>\w+)'),
            quick.model_mapper(User.objects.all(), 'assigned_to')),
        (re.compile(r'\^\+(?P<due>\d+)'),
            lambda v: {'due': date.today() + timedelta(days=int(v['due']))}),
        (re.compile(r'=(?P<estimated_hours>[\d\.]+)h'),
            quick.identity()),
        ]

    data, rest = quick.parse_quickadd(
        request.POST.get('quick', ''),
        QUICK_RULES)

    data['notes'] = ' '.join(rest)  # Everything which could not be parsed
                                    # is added to the ``notes`` field.
    form = TicketForm(data)

.. note::

   The mappers always get the regex matches ``dict`` and return a
   ``dict``.
"""

from __future__ import absolute_import, unicode_literals

from datetime import date, timedelta

from django.utils import dateformat
from django.utils.datastructures import MultiValueDict
from django.utils.encoding import force_text
from django.utils.translation import ugettext as _


def parse_quickadd(quick, regexes):
    """
    The main workhorse. Named ``parse_quickadd`` for historic reasons,
    can be used not only for adding but for searching etc. too. In fact,
    :class:`towel.forms.SearchForm` supports quick rules out of the box
    when they are specified in ``quick_rules``.
    """

    data = {}
    rest = []

    while quick:
        for regexp, extract in regexes:
            match = regexp.match(quick)
            if match:
                for key, value in extract(match.groupdict()).items():
                    data.setdefault(key, []).append(value)

                quick = quick[len(match.group(0)):].strip()
                break

        else:
            splitted = quick.split(' ', 1)
            if len(splitted) < 2:
                rest.append(quick)
                break

            rest.append(splitted[0])
            quick = splitted[1]

    return MultiValueDict(data), rest


def identity():
    """
    Identity mapper. Returns the values from the regular expression
    directly.
    """
    return (lambda value: value)


def model_mapper(queryset, attribute):
    """
    The regular expression needs to return a dict which is directly passed
    to ``queryset.get()``. As a speciality, this mapper returns both the
    primary key of the instance under the ``attribute`` name, and the instance
    itself as ``attribute_``.
    """
    def _fn(values):
        try:
            instance = queryset.get(**values)
            return {
                attribute: instance.pk,
                attribute + '_': instance,
            }
        except (queryset.model.DoesNotExist, KeyError, TypeError, ValueError):
            return {}
    return _fn


def static(**kwargs):
    """
    Return a predefined ``dict`` when the given regex matches.
    """
    return (lambda values: kwargs)


def model_choices_mapper(data, attribute):
    """
    Needs a ``value`` provided by the regular expression and returns
    the corresponding ``key`` value.

    Example::

        class Ticket(models.Model):
            VISIBILITY_CHOICES = (
                ('public', _('public')),
                ('private', _('private')),
                )
            visibility = models.CharField(choices=VISIBILITY_CHOICES)

        QUICK_RULES = [
            (re.compile(r'~(?P<value>[^\s]+)'), quick.model_choices_mapper(
                Ticket.VISIBILITY_CHOICES, 'visibility')),
            ]
    """
    def _fn(values):
        reverse = dict((force_text(value), key) for key, value in data)
        try:
            return {attribute: reverse[values['value']]}
        except KeyError:
            return {}
    return _fn


def due_mapper(attribute):
    """
    Understands ``Today``, ``Tomorrow``, the following five localized
    week day names or (partial) dates such as ``20.12.`` and ``01.03.2012``.
    """
    def _fn(values):
        today = date.today()
        due = values['due']

        days = [(dateformat.format(d, 'l'), d) for d in [
            (today + timedelta(days=d)) for d in range(2, 7)]]
        days.append((_('Today'), today))
        days.append((_('Tomorrow'), today + timedelta(days=1)))
        days = dict((k.lower(), value) for k, value in days)

        if due.lower() in days:
            return {attribute: days[due.lower()]}

        day = [today.year, today.month, today.day]
        try:
            for i, n in enumerate(due.split('.')):
                day[2 - i] = int(n, 10)
        except (IndexError, TypeError, ValueError):
            pass

        try:
            return {attribute: date(*day)}
        except (TypeError, ValueError):
            pass

        return {}
    return _fn


def bool_mapper(attribute):
    """
    Maps ``yes``, ``1`` and ``on`` to ``True`` and ``no``, ``0``
    and ``off`` to ``False``.
    """
    def _fn(values):
        if values['bool'].lower() in ('yes', '1', 'on', 'true'):
            return {attribute: True}
        elif values['bool'].lower() in ('no', '0', 'off', 'false'):
            return {attribute: False}
        return {}
    return _fn
