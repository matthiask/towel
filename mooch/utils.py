from django.db.models.manager import Manager
from django.db.models.query import QuerySet


def get_object_or_none(klass, *args, **kwargs):
    """
    Modelled after get_object_or_404
    """

    if isinstance(klass, QuerySet):
        queryset = klass
    elif isinstance(klass, Manager):
        queryset = klass.all()
    else:
        queryset = klass._default_manager.all()

    try:
        return queryset.get(*args, **kwargs)
    except (queryset.model.DoesNotExist, ValueError):
        return None
