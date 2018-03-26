Command Line Tool
=================

This command line tool can be used to process PII data into Cryptographic Longterm Keys.

The command line tool can be accessed in two ways:

- Using the ``clkutil`` script which should have been added to your path during installation.
- directly running the python module ``clkhash.cli`` with ``python -m clkhash.cli``.


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

The yaml schema used for the generated data is the following::

    - identifier: "INDEX"
      notes: "Ignored"
    - identifier: "NAME freetext"
    - identifier: "DOB YYYY/MM/DD"
    - identifier: "GENDER M or F"

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