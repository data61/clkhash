Command Line Tool
=================

``clkhash`` includes a command line tool which can be used to interact without writing Python code.
The primary use case is to encode personally identifiable data from a csv into Cryptographic Longterm Keys.

The command line tool can be accessed in two equivalent ways:

- Using the ``clkutil`` script which gets added to your path during installation.
- directly running the python module with ``python -m clkhash``.

A list of valid commands can be listed with the ``--help`` argument:

.. command-output:: clkutil --help


Command specific help
---------------------

The ``clkutil`` tool has help pages for all commands built in - simply append ``--help``
to the command.


Hashing
-------

The command line tool ``clkutil`` can be used to hash a csv file of personally identifiable information.
The tool needs to be provided with keys and a :ref:`schema`; it will output a file containing
json serialized hashes.

.. command-output:: clkutil hash --help


Example
~~~~~~~

Assume a csv (``fake-pii.csv``) contains rows like the following::


    0,Libby Slemmer,1933/09/13,F
    1,Garold Staten,1928/11/23,M
    2,Yaritza Edman,1972/11/30,F

It can be hashed using ``clkutil`` with::

    $ clkutil hash --schema simple-schema.json fake-pii.csv horse clk.json

Where:

- ``horse`` is the secret that both participants will use to hash their data.
- ``simple-schema.json`` is a :ref:`schema` describing how to hash the csv. E.g, ignore the first
  column, use bigram tokens of the name, use positional unigrams of the date of birth etc.
- ``clk.json`` is the output file.

Describing
----------

Users can inspect the distribution of the number of bits set in ``CLKs`` by using the ``describe`` command.

.. command-output:: clkutil describe --help


Example
~~~~~~~

::

    $ clkutil describe example_clks_a.json


     339|                                   oo
     321|                                  ooo
     303|                                  ooo
     285|                                  ooo o
     268|                                  oooooo
     250|                                oooooooo
     232|                                oooooooo
     214|                               ooooooooo
     196|                             o ooooooooo o
     179|                             o ooooooooooo
     161|                             oooooooooooooo
     143|                            ooooooooooooooo
     125|                           oooooooooooooooo
     107|                           oooooooooooooooooo
      90|                         ooooooooooooooooooooo
      72|                         oooooooooooooooooooooo
      54|                        oooooooooooooooooooooooo
      36|                      ooooooooooooooooooooooooooo
      18|                   oooooooooooooooooooooooooooooooo
       1| o  o  ooooooooooooooooooooooooooooooooooooooooooooooooooo oo
         ------------------------------------------------------------
         4 4 4 4 4 4 4 4 5 5 5 5 5 5 5 5 5 6 6 6 6 6 6 6 6 6 7 7 7 7
         1 2 3 4 5 6 7 9 0 1 2 3 4 5 7 8 9 0 1 2 3 5 6 7 8 9 0 1 3 4
         0 1 2 4 5 7 8 0 1 2 4 5 7 8 0 1 2 4 5 7 8 0 1 2 4 5 7 8 0 1
           . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
           4 8 3 7 1 6 0 4 9 3 7 2 6 0 5 9 3 8 2 6 1 5 9 4 8 2 7 1 5

    -------------------------
    |        Summary        |
    -------------------------
    |   observations: 5000  |
    | min value: 410.000000 |
    |   mean : 601.571600   |
    | max value: 753.000000 |
    -------------------------


.. note::

    It is an indication of problems in the hashing if the distribution is skewed towards no bits set or
    all bits set. Consult the :doc:`tutorial_cli` for further details.


.. _schema_handling:

Schema Handling
---------------

A schema file can be tested for validity against the schema specification with the ``validate-schema`` command.

.. command-output:: clkutil validate-schema --help

Example
~~~~~~~

::

     $ clkutil validate-schema clkhash/data/randomnames-schema.json
     schema is valid


Schema files of older versions can be converted to the latest version with the ``convert-schema`` command.

.. command-output:: clkutil convert-schema --help


.. _data-generation:

Data Generation
---------------

The command line tool has a ``generate`` command for generating fake pii data.

.. command-output:: clkutil generate --help


::

    $ clkutil generate 1000 fake-pii-out.csv
    $ head -n 4  fake-pii-out.csv
    INDEX,NAME freetext,DOB YYYY/MM/DD,GENDER M or F
    0,Libby Slemmer,1933/09/13,F
    1,Garold Staten,1928/11/23,M
    2,Yaritza Edman,1972/11/30,F




A corresponding hashing schema can be generated as well::

    $ clkutil generate-default-schema schema.json
    $ cat schema.json
    {
      "version": 1,
      "clkConfig": {
        "l": 1024,
        "k": 30,
        "hash": {
          "type": "doubleHash"
        },
        "kdf": {
          "type": "HKDF",
          "hash": "SHA256",
          "salt": "SCbL2zHNnmsckfzchsNkZY9XoHk96P/G5nUBrM7ybymlEFsMV6PAeDZCNp3rfNUPCtLDMOGQHG4pCQpfhiHCyA==",
          "info": "c2NoZW1hX2V4YW1wbGU=",
          "keySize": 64
        }
      },
      "features": [
        {
          "identifier": "INDEX",
          "format": {
            "type": "integer"
          },
          "hashing": {
            "ngram": 1,
            "weight": 0
          }
        },
        {
          "identifier": "NAME freetext",
          "format": {
            "type": "string",
            "encoding": "utf-8",
            "case": "mixed",
            "minLength": 3
          },
          "hashing": {
            "ngram": 2,
            "weight": 0.5
          }
        },
        {
          "identifier": "DOB YYYY/MM/DD",
          "format": {
            "type": "string",
            "encoding": "ascii",
            "description": "Numbers separated by slashes, in the year, month, day order",
            "pattern": "(?:\\d\\d\\d\\d/\\d\\d/\\d\\d)\\Z"
          },
          "hashing": {
            "ngram": 1,
            "positional": true
          }
        },
        {
          "identifier": "GENDER M or F",
          "format": {
            "type": "enum",
            "values": ["M", "F"]
          },
          "hashing": {
            "ngram": 1,
            "weight": 2
          }
        }
      ]
    }


Benchmark
---------

A quick hashing benchmark can be carried out to determine the rate at which the current machine
can generate 10000 clks from a simple schema (data as generated :ref:`above <data-generation>`)::

    python -m clkhash.cli benchmark
    generating CLKs: 100%                 10.0K/10.0K [00:01<00:00, 7.72Kclk/s, mean=521, std=34.7]
     10000 hashes in 1.350489 seconds. 7.40 KH/s



As a rule of thumb a single modern core will hash around 1M entities in about 20 minutes.

.. note::

    Hashing speed is effected by the number of features and the corresponding schema. Thus these
    numbers will, in general, not be a good predictor for the performance of a specific use-case.

The output shows a running mean and std deviation of the generated clks' popcounts. This can be used
as a basic sanity check - ensure the CLK's popcount is not around 0 or 1024.

Interaction with Entity Service
-------------------------------

There are several commands that interact with a REST api for carrying out privacy preserving linking.
These commands are:

- status
- create-project
- create
- upload
- results

See also the :doc:`Tutorial for CLI<tutorials>`.
