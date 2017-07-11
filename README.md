# CLK Hash

Python implementation of cryptographic linkage keys.

This is as described by Rainer Schnell, Tobias Bachteler, and Jörg Reiher in [A Novel Error-Tolerant Anonymous Linking Code](http://www.record-linkage.de/-download=wp-grlc-2011-02.pdf)


# Installation

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
    $ clkutil hash fake-pii-out.csv horse staple /tmp/fake-clk.json
    Assuming default schema
    Hashing data
    CLK data written to /tmp/fake-clk.json


Note the hash command takes two keys, these should only be shared with
the other entity - and not with the service carrying out the linkage.

To use the clkutil without installation just run:

    python -m clkhash.cli


# Tests

Run unit tests with nose

```
$ python -m nose
......................SS..............................
----------------------------------------------------------------------
Ran 54 tests in 6.615s

OK (SKIP=2)
```

Note several tests will be skipped by default. To enable the command
line tests set the  `INCLUDE_CLI` environment variable. To enable
the tests which interact with an entity service set the
`TEST_ENTITY_SERVICE` environment variable to the target service's 
address.


Limitations
-----------

- Hashing doesn't utilize multiple CPUs.

