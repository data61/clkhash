Development
===========


.. toctree::
   :maxdepth: 2

   clkhash

Testing
-------

Make sure you have all the required modules before running the tests
(modules that are only needed for tests are not included during
installation)::


    $ poetry install


Now run the unit tests and print out code coverage with `py.test`::

    $ python -m pytest --cov=clkhash


Note several tests will be skipped by default.

Type Checking
-------------


``clkhash`` uses static typechecking with ``mypy``. To run the type checker (in Python 3.5 or later)::

    $ pip install mypy
    $ mypy clkhash --ignore-missing-imports --strict-optional --no-implicit-optional --disallow-untyped-calls


