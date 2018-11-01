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


    $ pip install -r requirements.txt


Now run the unit tests and print out code coverage with `py.test`::

    $ python -m pytest --cov=clkhash


Note several tests will be skipped by default. To enable the command
line tests set the  `INCLUDE_CLI` environment variable. To enable
the tests which interact with an entity service set the
`TEST_ENTITY_SERVICE` environment variable to the target service's
address::

    $ TEST_ENTITY_SERVICE= INCLUDE_CLI= python -m pytest --cov=clkhash


Type Checking
-------------


``clkhash`` uses static typechecking with ``mypy``. To run the type checker (in Python 3.5 or later)::

    $ pip install mypy
    $ mypy clkhash --ignore-missing-imports --strict-optional --no-implicit-optional --disallow-untyped-calls


Packaging
---------

The ``clkutil`` command line tool can be frozen into an exe using PyInstaller::

    pyinstaller cli.spec


Look for `clkutil.exe` in the `dist` directory.
