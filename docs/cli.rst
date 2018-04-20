Command Line Tool
=================

This command line tool can be used to process PII data into Cryptographic Longterm Keys.

The command line tool can be accessed in two ways:

- Using the ``clkutil`` script which should have been added to your path during installation.
- directly running the python module ``clkhash.cli`` with ``python -m clkhash.cli``.


Help
-----

The ``clkutil`` tool has help pages for all commands built in.::

    $ clkutil hash --help
    Usage: clkutil hash [OPTIONS] INPUT KEYS... SCHEMA OUTPUT

      Process data to create CLKs

      Given a file containing csv data as INPUT, and a json document defining
      the expected schema, verify the schema, then hash the data to create CLKs
      writing to OUTPUT. Note the CSV file should contain a header row - however
      this row is not used by this tool.

      It is important that the keys are only known by the two data providers.
      Two words should be provided. For example:

      $clkutil hash input.txt horse staple output.txt

      Use "-" to output to stdout.

    Options:
      -q, --quiet             Quiet any progress messaging
      --no-header             Don't skip the first row
      --check-header BOOLEAN  If true, check the header against the schema
      --validate BOOLEAN      If true, validate the entries against the schema
      --help                  Show this message and exit.



Hashing
-------

The command line tool ``clkutil`` can be used to hash a csv file of personally identifiable information.
The tool needs to be provided with keys and a :ref:`schema`; it will output a file containing
json serialized hashes.


Example
~~~~~~~

Assume a csv (``fake-pii.csv``) contains rows like the following::


    0,Libby Slemmer,1933/09/13,F
    1,Garold Staten,1928/11/23,M
    2,Yaritza Edman,1972/11/30,F

It can be hashed using ``clkutil`` with::

    $ clkutil hash --schema simple-schema.json fake-pii.csv horse staple clk.json

Where:

- ``horse staple`` is the two part secret key that both participants will use to hash their data.
- ``simple-schema.json`` is a :ref:`schema` describing how to hash the csv. E.g, ignore the first
  column, use bigram tokens of the name, use positional unigrams of the date of birth etc.
- ``clk.json`` is the output file.

.. _data-generation:

Data Generation
---------------

The cli tool has an option for generating fake pii data.
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
- create
- upload
- results

See also the :doc:`Tutorial for CLI<tutorials>`.