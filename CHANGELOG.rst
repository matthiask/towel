Change log
==========

Next version
~~~~~~~~~~~~

0.32 (2026-10-25)
~~~~~~~~~~~~~~~~~

- Updated the README and the installation docs with current installation
  instructions and supported Python and Django versions. (#11)
- Moved the documentation to Read the Docs and fixed the docs build with
  current Sphinx releases.
- Switched the test suite to pytest, run through tox.
- Replaced Travis CI with GitHub Actions. Added Python 3.9 to 3.15 and Django
  3.2, 4.2, 5.2, 6.0 and 6.1 to the CI matrix.
- Started publishing releases to PyPI using trusted publishing.
- Converted the packaging metadata to ``pyproject.toml`` and switched the
  build backend to hatchling.


`0.31`_ (2023-10-31)
~~~~~~~~~~~~~~~~~~~~

- Fixed a few typos.
- Fixed an import.
- Updated ``tox.ini`` to use ``allowlist_externals``.


`0.30`_ (2022-05-19)
~~~~~~~~~~~~~~~~~~~~

- **BACKWARDS INCOMPATIBLE:** Raised the minimum Django version to 3.2.
- Dropped the dependency on ``six``.
- Fixed deprecation warnings.


`0.13.1`_ (2020-05-23)
~~~~~~~~~~~~~~~~~~~~~~

- Added the missing ``renderer`` argument to the ``render()`` methods of the
  autocompletion widgets.


`0.13`_ (2020-05-23)
~~~~~~~~~~~~~~~~~~~~

- Added Django 3.0 and 3.1 to the CI matrix.
- Removed a few compatibility fallbacks for old Django versions.


`0.12.1`_ (2019-11-25)
~~~~~~~~~~~~~~~~~~~~~~

- Stopped using ``field.rel.to``, which doesn't exist anymore.


`0.12`_ (2019-11-25)
~~~~~~~~~~~~~~~~~~~~

- **BACKWARDS INCOMPATIBLE:** Dropped Python 2 compatibility. The minimum
  Django version is now 1.11.
- Used ``MiddlewareMixin`` for the middleware.
- Replaced ``django.utils.six`` with ``six``.
- Made the ``build_attrs`` invocation compatible with newer Django versions.
- Reformatted the code using black.


`0.11`_ (2018-03-06)
~~~~~~~~~~~~~~~~~~~~

- Added ``towel.queryset_transform`` (taken from FeinCMS).
- Avoided a ``permalink()`` deprecation warning.
- Added fallback imports for newer Django versions.


`0.10.1`_ (2017-05-04)
~~~~~~~~~~~~~~~~~~~~~~

- Switched ``towel.mt`` to the app registry in ``django.apps``.


`0.10.0`_ (2017-03-26)
~~~~~~~~~~~~~~~~~~~~~~

- Updated ``ModelView.render`` for recent Django versions.


`0.9.0`_ (2016-11-21)
~~~~~~~~~~~~~~~~~~~~~

- Fixed incompatibilities with Django 1.10 and added it to the CI matrix.


`0.8.1`_ (2016-05-29)
~~~~~~~~~~~~~~~~~~~~~

- Stopped using ``patterns()``.


`0.8.0`_ (2016-01-18)
~~~~~~~~~~~~~~~~~~~~~

- **BACKWARDS INCOMPATIBLE:** Removed the API code (``towel.api``).
- Replaced ``commit_on_success`` with ``transaction.atomic`` for Django 1.8
  compatibility.
- Wrapped HTML-returning template tags with ``mark_safe()``.
- Allowed relative redirects.


`0.7.0`_ (2014-09-08)
~~~~~~~~~~~~~~~~~~~~~

- Fixed a crash when generating the related objects error message.
- Fixed a problem with encoding umlauts inside search forms.
- Added some logging.


`0.6.0`_ (2014-01-03)
~~~~~~~~~~~~~~~~~~~~~

- Fixed a few ``unicode()`` calls in untested code paths.
- Fixed handling of strings where iterables were expected.


`0.5.0`_ (2013-12-31)
~~~~~~~~~~~~~~~~~~~~~

- Added Python 3.2 compatibility.
- Stopped translating strings too early.


`0.4.0`_ (2013-12-21)
~~~~~~~~~~~~~~~~~~~~~

- **BACKWARDS INCOMPATIBLE:** Renamed a few ``DeleteView`` methods to make
  it easier to write ``ModelResourceView`` mixins.


`0.3.2`_ (2013-12-10)
~~~~~~~~~~~~~~~~~~~~~

- Fixed Python 2.6 compatibility.
- Started running the tests on Travis CI.


`0.3.1`_ (2013-11-26)
~~~~~~~~~~~~~~~~~~~~~

- Reused ``Manager.from_queryset`` if available and fixed ``get_query_set``
  deprecation warnings.


`0.3.0`_ (2013-11-26)
~~~~~~~~~~~~~~~~~~~~~

- **BACKWARDS INCOMPATIBLE:** Rewrote ``resource_url_fn`` with less magic.
- Replaced ``{% cycle %}`` in templates with CSS.


`0.2.2`_ (2013-11-25)
~~~~~~~~~~~~~~~~~~~~~

- Reorganized ``towel.api`` to avoid imports inside functions.
- Silenced ``module_name`` deprecation warnings.


`0.2.1`_ (2013-11-18)
~~~~~~~~~~~~~~~~~~~~~

- Switched to setuptools and added the Python 3 trove classifier.
- Moved the most useful modelview template tags to ``towel_resources``.


`0.2.0`_ (2013-11-18)
~~~~~~~~~~~~~~~~~~~~~

`0.1`_ (2012-08-28)
~~~~~~~~~~~~~~~~~~~

`0.0.5`_ (2012-04-02)
~~~~~~~~~~~~~~~~~~~~~

`0.0.4`_ (2012-03-15)
~~~~~~~~~~~~~~~~~~~~~

`0.0.3`_ (2012-03-13)
~~~~~~~~~~~~~~~~~~~~~

`0.0.2`_ (2011-12-23)
~~~~~~~~~~~~~~~~~~~~~

- Initial release!

.. _0.0.2: https://github.com/matthiask/towel/commit/v0.0.2
.. _0.0.3: https://github.com/matthiask/towel/compare/v0.0.2...v0.0.3
.. _0.0.4: https://github.com/matthiask/towel/compare/v0.0.3...v0.0.4
.. _0.0.5: https://github.com/matthiask/towel/compare/v0.0.4...9e7151f
.. _0.1: https://github.com/matthiask/towel/compare/9e7151f...v0.1.0
.. _0.2.0: https://github.com/matthiask/towel/compare/v0.1.0...69b983b
.. _0.2.1: https://github.com/matthiask/towel/compare/69b983b...v0.2.1
.. _0.2.2: https://github.com/matthiask/towel/compare/v0.2.1...v0.2.2
.. _0.3.0: https://github.com/matthiask/towel/compare/v0.2.2...v0.3.0
.. _0.3.1: https://github.com/matthiask/towel/compare/v0.3.0...v0.3.1
.. _0.3.2: https://github.com/matthiask/towel/compare/v0.3.1...v0.3.2
.. _0.4.0: https://github.com/matthiask/towel/compare/v0.3.2...v0.4.0
.. _0.5.0: https://github.com/matthiask/towel/compare/v0.4.0...v0.5.0
.. _0.6.0: https://github.com/matthiask/towel/compare/v0.5.0...v0.6.0
.. _0.7.0: https://github.com/matthiask/towel/compare/v0.6.0...v0.7.0
.. _0.8.0: https://github.com/matthiask/towel/compare/v0.7.0...v0.8.0
.. _0.8.1: https://github.com/matthiask/towel/compare/v0.8.0...v0.8.1
.. _0.9.0: https://github.com/matthiask/towel/compare/v0.8.1...6892788
.. _0.10.0: https://github.com/matthiask/towel/compare/6892788...0c33452
.. _0.10.1: https://github.com/matthiask/towel/compare/0c33452...1c7028c
.. _0.11: https://github.com/matthiask/towel/compare/1c7028c...d4d0ad7
.. _0.12: https://github.com/matthiask/towel/compare/d4d0ad7...1770329
.. _0.12.1: https://github.com/matthiask/towel/compare/1770329...d00fb74
.. _0.13: https://github.com/matthiask/towel/compare/d00fb74...5ee38aa
.. _0.13.1: https://github.com/matthiask/towel/compare/5ee38aa...36f7ee5
.. _0.30: https://github.com/matthiask/towel/compare/36f7ee5...438bd76
.. _0.31: https://github.com/matthiask/towel/compare/438bd76...5020539
