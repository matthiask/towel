import re

from django.db import models
from django.db.models import Q


def normalize_query(query_string,
                    findterms=re.compile(r'"([^"]+)"|(\S+)').findall,
                    normspace=re.compile(r'\s{2,}').sub):
    ''' Splits the query string in invidual keywords, getting rid of unecessary spaces
        and grouping quoted words together.
        Example:

        >>> normalize_query('  some random  words "with   quotes  " and   spaces')
        ['some', 'random', 'words', 'with quotes', 'and', 'spaces']

    '''
    return [normspace(' ', (t[0] or t[1]).strip()) for t in findterms(query_string)]


class SearchManager(models.Manager):
    search_fields = ()

    def _search(self, query):
        queryset = self.get_query_set()

        if not query or not self.search_fields:
            return queryset

        for keyword in normalize_query(query):
            negate = False
            if len(keyword)>1:
                if keyword[0] == '-':
                    keyword = keyword[1:]
                    negate = True
                elif keyword[0] == '+':
                    keyword = keyword[1:]

            if negate:
                q = reduce(lambda p, q: p&q,
                    (~Q(**{'%s__icontains' % field: keyword}) for field in self.search_fields),
                    Q())
            else:
                q = reduce(lambda p, q: p|q,
                    (Q(**{'%s__icontains' % field: keyword}) for field in self.search_fields),
                    Q())

            queryset = queryset.filter(q)

        return queryset
