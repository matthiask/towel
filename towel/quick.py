from datetime import date, timedelta

from django.utils import dateformat
from django.utils.datastructures import MultiValueDict
from django.utils.translation import ugettext as _


def parse_quickadd(quick, regexes):
    data = {}
    rest = []

    while quick:
        for r, p in regexes:
            match = r.match(quick)
            if match:
                for k, v in p(match.groupdict()).items():
                    data.setdefault(k, []).append(v)

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
    def _fn(v):
        return v
    return _fn


def model_mapper(queryset, attribute):
    def _fn(v):
        try:
            instance = queryset.get(**v)
            return {
                attribute: instance.pk,
                attribute + '_': instance,
                }
        except (queryset.model.DoesNotExist, KeyError, TypeError, ValueError):
            return {}
    return _fn


def static(**kwargs):
    def _fn(v):
        return kwargs
    return _fn


def model_choices_mapper(data, attribute):
    """
    Needs a ``value`` provided by the regular expression and returns
    the corresponding ``key`` value.
    """
    reverse = dict((unicode(v), k) for k, v in data)
    def _fn(v):
        try:
            return {attribute: reverse[v['value']]}
        except KeyError:
            return {}
    return _fn


def due_mapper(attribute):
    def _fn(v):
        today = date.today()
        due = v['due']

        days = [(dateformat.format(d, 'l'), d) for d in [
            (today + timedelta(days=d)) for d in range(2, 7)]]
        days.append((_('Today'), today))
        days.append((_('Tomorrow'), today + timedelta(days=1)))
        days = dict((k.lower(), v) for k, v in days)

        if due.lower() in days:
            return {attribute: days[due.lower()]}

        day = [today.year, today.month, today.day]
        try:
            for i, n in enumerate(due.split('.')):
                day[2-i] = int(n, 10)
        except (IndexError, TypeError, ValueError):
            pass

        try:
            return {attribute: date(*day)}
        except (TypeError, ValueError):
            pass

        return {}
    return _fn
