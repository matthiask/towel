=================================================
towel-multitenancy - we support all buzzwords now
=================================================

Assumptions
===========

* The following settings are required:

  * ``TOWEL_MT_CLIENT_MODEL``:
    The tenant model, e.g. ``clients.Client``.
  * ``TOWEL_MT_ACCESS_MODEL``:
    The model linking a Django user with a client, must have the following
    fields:

      * ``user``: Foreign key to ``auth.User``.
      * ``access``: An integer describing the access level of the given user.
        Higher numbers mean higher access. You have to define those numbers
        yourself.
      * The lowercased class name of the client model above as a foreign key
        to the client model. If your client model is named ``Customer``, the
        name of this foreign key must be ``customer``.

* All model managers have a ``for_access()`` method with a single argument,
  an instance of the access model, which returns a queryset containing only
  the objects the current user is allowed to see. The access model should be
  available as ``request.access``, which means that you are free to put
  anything there which can be understood by the ``for_access()`` methods. The
  ``request.access`` attribute is made available by the
  ``towel.mt.middleware.LazyAccessMiddleware`` middleware.
* ``towel.mt.modelview.ModelView`` automatically fills in a ``created_by``
  foreign key pointing to ``auth.User`` if it exists.
* The form classes in ``towel.mt.forms``, those being ``ModelForm``, ``Form``
  and ``SearchForm`` all require the request (the two former on initialization,
  the latter on ``post_init``). Model choice fields are postprocessed to only
  contain values from the current tenant. This does not work if you customize
  the ``choices`` field at the same time as setting the ``queryset``. If you
  do that you're on your own.
* The model authentication backend ``towel.mt.auth.ModelBackend`` also allows
  e-mail addresses as username. It preloads the access and client model and
  assigns it to ``request.user`` if possible. This is purely a convenience --
  you are not required to use the backend.


Further information and links
=============================

* Towel on github: https://github.com/matthiask/towel/
