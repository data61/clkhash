# CLK Hash

Python implementation of cryptographic linkage key hashing.

This is as described by Rainer Schnell, Tobias Bachteler, and Jörg Reiher in
[A Novel Error-Tolerant Anonymous Linking Code](http://www.record-linkage.de/-download=wp-grlc-2011-02.pdf)


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


    $ clkutil generate 1000 fake-pii-out.csv
    $ head -n 4  fake-pii-out.csv
    INDEX,NAME freetext,DOB YYYY/MM/DD,GENDER M or F
    0,Libby Slemmer,1933/09/13,F
    1,Garold Staten,1928/11/23,M
    2,Yaritza Edman,1972/11/30,F
    
To hash this data using the default schema, with the secret key `horse staple`:

    $ clkutil hash fake-pii-out.csv horse staple /tmp/fake-clk.json
    Assuming default schema
    Hashing data
    CLK data written to /tmp/fake-clk.json


Note the keys should only be shared with the other entity - and not with the service carrying out the linkage.

To use the clkutil without installation (after installing the dependencies) just run:

    python -m clkhash.cli

## Benchmark

```
$ python -m clkhash.cli benchmark
100000 x 1024 bit popcounts in 0.018481 seconds
Popcount speed: 660.52 MiB/s
 10000 hashes in 1.767731 seconds. 5.66 KH/s
```

As a rule of thumb a single modern core will hash around 1M entities in about 20 minutes.


# Tests

Run unit tests with nose

```
$ python -m nose
......................SS..............................
----------------------------------------------------------------------
Ran 51 tests in 0.915s

OK (SKIP=2)
```

Note several tests will be skipped by default. To enable the command
line tests set the  `INCLUDE_CLI` environment variable. To enable
the tests which interact with an entity service set the
`TEST_ENTITY_SERVICE` environment variable to the target service's 
address.
