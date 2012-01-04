"""
Drop-in replacement for Django's ``django.core.paginator`` with additional goodies
"""

from django.conf import settings
from django.core import paginator


# Import useful exceptions into the local scope
InvalidPage = paginator.InvalidPage
PageNotAnInteger = paginator.PageNotAnInteger
EmptyPage = paginator.EmptyPage


#: Paginator configuration
PAGINATION = getattr(settings, 'PAGINATION', {
    'START': 6, # items at the start
    'END': 6, # items at the end
    'AROUND': 5, # items around the current page
    })


def filter_adjacent(iterable):
    """Collapse identical adjacent values"""
    current = type('Marker', (object,), {}) # Generate an object guaranteed to
                                            # not exist inside the iterable

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
        self.__dict__ = page.__dict__

    @property
    def page_range(self):
        """
        Generates a list for displaying Digg-style pagination

        The page numbers which are left out are indicated with a ``None`` value.
        Please note that Django's paginator own ``page_range`` method isn't
        overwritten -- Django's ``page_range`` is a method of the ``Paginator``
        class, not the ``Page`` class.

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
                yield None # Ellipsis marker

