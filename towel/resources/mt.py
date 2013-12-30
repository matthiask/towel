from __future__ import absolute_import, unicode_literals

from django.core.exceptions import ImproperlyConfigured

from towel.utils import safe_queryset_and


class MultitenancyMixin(object):
    def get_queryset(self):
        if self.queryset is not None:
            return safe_queryset_and(
                self.queryset,
                self.queryset.model._default_manager.for_access(
                    self.request.access))
        elif self.model is not None:
            return self.model._default_manager.for_access(
                self.request.access)
        else:
            raise ImproperlyConfigured(
                "'%s' must define 'queryset' or 'model'"
                % self.__class__.__name__)

    def get_parent_queryset(self):
        # towel.resources.inlines.ChildFormView
        return self.get_parent_class()._default_manager.for_access(
            self.request.access)

    def get_form_kwargs(self, **kwargs):
        kwargs['request'] = self.request
        return super(MultitenancyMixin, self).get_form_kwargs(**kwargs)
