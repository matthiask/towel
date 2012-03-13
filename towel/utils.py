from django.db.models.deletion import Collector


def related_classes(instance):
    """
    Return all classes which would be deleted if the passed instance
    were deleted too by employing the cascade machinery of Django
    itself. Does **not** return instances, only classes.
    """
    collector = Collector(using=instance._state.db)
    collector.collect([instance])

    # Save collected objects for later referencing (well yes, it does return
    # instances but we don't have to tell anybody :-)
    instance._collected_objects = collector.data

    return collector.data.keys()


def safe_queryset_and(qs1, qs2):
    """
    Safe AND-ing of two querysets. If one of both queries has its
    DISTINCT flag set, sets distinct on both querysets. Also takes extra
    care to preserve the result of the following queryset methods:

    * ``reverse()``
    * ``transform()``
    * ``select_related()``
    """

    if qs1.query.distinct or qs2.query.distinct:
        res = qs1.distinct() & qs2.distinct()
    else:
        res = qs1 & qs2

    res._transform_fns = list(set(
        getattr(qs1, '_transform_fns', [])
        + getattr(qs2, '_transform_fns', [])))

    if not (qs1.query.standard_ordering and qs2.query.standard_ordering):
        res.query.standard_ordering = False

    select_related = [qs1.query.select_related, qs2.query.select_related]
    if False in select_related:
        select_related.remove(False) # We are not interested in the default value

    if len(select_related) == 1:
        res.query.select_related = select_related[0]
    elif len(select_related) == 2:
        if True in select_related:
            select_related.remove(True) # prefer explicit select_related to generic select_related()

        if len(select_related) > 0:
            # If we have two explicit select_related calls, take any of them
            res.query.select_related = select_related[0]
        else:
            res = res.select_related()

    return res
