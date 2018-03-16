# CLK Hash

Python implementation of cryptographic linkage key hashing. Supports Python versions 2.7+, 3.4+

This is as described by Rainer Schnell, Tobias Bachteler, and Jörg Reiher in
[A Novel Error-Tolerant Anonymous Linking Code](http://www.record-linkage.de/-download=wp-grlc-2011-02.pdf)

[![Documentation Status](https://readthedocs.org/projects/clkhash/badge/?version=latest)](http://clkhash.readthedocs.io/en/latest/?badge=latest)


# Installation

Install the dependencies with:

    pip install -r requirements.txt


Test and install with:

    python setup.py test
    pip install -e .


# CLI Tool

After installation of the clkhash library you should have a `clkutil` program in your path.

This can be used to process PII data into Cryptographic Longterm Keys.
The tool also has an option for generating fake pii data, and commands to upload hashes to an entity matching service.

```
$ clkutil generate 1000 fake-pii-out.csv
$ head -n 4  fake-pii-out.csv
INDEX,NAME freetext,DOB YYYY/MM/DD,GENDER M or F
0,Libby Slemmer,1933/09/13,F
1,Garold Staten,1928/11/23,M
2,Yaritza Edman,1972/11/30,F
```
 
To hash this data using the default schema, with the shared secret keys `horse staple`:

    $ clkutil hash fake-pii-out.csv horse staple /tmp/fake-clk.json
    CLK data written to /tmp/fake-clk.json


Note the keys should only be shared with the other entity - and not with anyone carrying out 
the record linkage.

To use the clkutil without installation (after installing the dependencies) just run:

    python -m clkhash.cli

# clkhash api

To hash a csv file of entities using the default schema:

```python
from clkhash import clk, schema
default_schema = schema.get_schema_types(schema.load_schema(None))
clks = clk.generate_clk_from_csv(open('fake-pii-out.csv','r'), ('key1', 'key2'), default_schema)
```

## Benchmark

```
$ python -m clkhash.cli benchmark
10000 hashes in 1.524871 seconds. 6.56 KH/s
```

As a rule of thumb a single modern core will hash around 1M entities in about 20 minutes.


# Tests

Run unit tests with nose

```
$ python -m nose
```

Note several tests will be skipped by default. To enable the command
line tests set the  `INCLUDE_CLI` environment variable. To enable
the tests which interact with an entity service set the
`TEST_ENTITY_SERVICE` environment variable to the target service's 
address.

```
$ TEST_ENTITY_SERVICE= INCLUDE_CLI= python -m nose
```


# Static Typechecking

```
$ mypy clkhash --ignore-missing-imports --strict-optional --no-implicit-optional --disallow-untyped-calls
```