"""
Drop-in replacement for Django's ``django.core.paginator`` with additional
goodness

Django's paginator class has a ``page_range`` method returning a list of all
available pages. If you got lots and lots of pages this is not very helpful.
Towel's page class (**not** paginator class!) sports a ``page_range`` method
too which only returns a few pages at the beginning and at the end of the page
range and a few pages around the current page.

All you have to do to use this module is replacing all imports from
``django.core.paginator`` with ``towel.paginator``. All important classes and
all exceptions are available inside this module too.

The page range parameters can be customized by adding a ``PAGINATION`` setting.
The defaults are as follows::

    PAGINATION = {
        'START': 6, # pages at the beginning of the range
        'END': 6, # pages at the end of the range
        'AROUND': 5, # pages around the current page
        }
"""

from __future__ import absolute_import, unicode_literals

from django.conf import settings
from django.core import paginator


__all__ = ('InvalidPage', 'PageNotAnInteger', 'EmptyPage', 'Paginator', 'Page')


# Import useful exceptions into the local scope
InvalidPage = paginator.InvalidPage
PageNotAnInteger = paginator.PageNotAnInteger
EmptyPage = paginator.EmptyPage


#: Paginator configuration
PAGINATION = getattr(settings, 'PAGINATION', {
    'START': 6,   # items at the start
    'END': 6,     # items at the end
    'AROUND': 5,  # items around the current page
})


def filter_adjacent(iterable):
    """Collapse identical adjacent values"""
    # Generate an object guaranteed to not exist inside the iterable
    current = type(str('Marker'), (object,), {})

    for item in iterable:
        if item != current:
            current = item
            yield item


class Paginator(paginator.Paginator):
    """
    Custom paginator returning a Page object with an additional page_range
    method which can be used to implement Digg-style pagination
    """
    def page(self, number):
        return Page(paginator.Paginator.page(self, number))


class Page(paginator.Page):
    """
    Page object for Digg-style pagination
    """
    def __init__(self, page):
        # We do not call super.__init__, because we're only a wrapper / proxy
        self.__dict__ = page.__dict__

    @property
    def page_range(self):
        """
        Generates a list for displaying Digg-style pagination

        The page numbers which are left out are indicated with a ``None``
        value.  Please note that Django's paginator own ``page_range`` method
        isn't overwritten -- Django's ``page_range`` is a method of the
        ``Paginator`` class, not the ``Page`` class.

        Usage::

            {% for p in page.page_range %}
                {% if p == page.number %}
                    {{ p }} <!-- current page -->
                {% else %}
                    {% if p is None %}
                        &hellip;
                    {% else %}
                        <a href="?page={{ p }}">{{ p }}</a>
                    {% endif %}
                {% endif %}
            {% endfor %}
        """
        return filter_adjacent(self._generate_page_range())

    def _generate_page_range(self):
        num_pages = self.paginator.num_pages

        for i in range(1, num_pages + 1):
            if i <= PAGINATION['START']:
                yield i

            elif i > num_pages - PAGINATION['END']:
                yield i

            elif abs(self.number - i) <= PAGINATION['AROUND']:
                yield i

            else:
                yield None  # Ellipsis marker
