# CLK Hash

Python implementation of cryptographic longterm key hashing. Supports Python versions 2.7+, 3.4+

This is as described by Rainer Schnell, Tobias Bachteler, and Jörg Reiher in
[A Novel Error-Tolerant Anonymous Linking Code](http://www.record-linkage.de/-download=wp-grlc-2011-02.pdf)

[![Documentation Status](https://readthedocs.org/projects/clkhash/badge/?version=latest)](http://clkhash.readthedocs.io/en/latest/?badge=latest)


## Installation

Install clkhash with all dependencies using pip:

    pip install clkhash

If the installation of `bitarray` fails on Windows you may need to install the appropriate
[Visual Studio C++ compiler](https://wiki.python.org/moin/WindowsCompilers) for your version
of Python; this is required because the `bitarray` library compiles a C extension.

## Documentation

[https://clkhash.readthedocs.io](https://clkhash.readthedocs.io/en/latest/)


## CLI Tool

After installation of the clkhash library you should have a `clkutil` program in your path.
Alternatively you can use `python -m clkhash.cli`.

This command line tool can be used to process PII data into Cryptographic Longterm Keys.
The tool also has an option for generating fake PII data, and commands to upload hashes to an 
entity matching service.

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

To use the command line tool without installing `clkhash`, install the dependencies, then run:

    python -m clkhash.cli

## clkhash api

To hash a CSV file of entities using the default schema:

```python
from clkhash import clk, schema
default_schema = schema.get_schema_types(schema.load_schema(None))
clks = clk.generate_clk_from_csv(open('fake-pii-out.csv','r'), ('key1', 'key2'), default_schema)
```

