# CLK Hash

Python implementation of cryptographic longterm key hashing. `clkhash` supports Python versions 3.6+

This is as described by Rainer Schnell, Tobias Bachteler, and Jörg Reiher in
[A Novel Error-Tolerant Anonymous Linking Code](http://grlc.german-microsimulation.de/wp-content/uploads/2017/05/downloadwp-grlc-2011-02.pdf)

[![codecov](https://codecov.io/gh/data61/clkhash/branch/master/graph/badge.svg)](https://codecov.io/gh/data61/clkhash)
[![Documentation Status](https://readthedocs.org/projects/clkhash/badge/?version=latest)](http://clkhash.readthedocs.io/en/latest/?badge=latest)
[![Build Status](https://travis-ci.org/data61/clkhash.svg?branch=master)](https://travis-ci.org/data61/clkhash)
[![Build Status](https://dev.azure.com/data61/Anonlink/_apis/build/status/data61.clkhash?branchName=master)](https://dev.azure.com/data61/Anonlink/_build/latest?definitionId=2&branchName=master)
[![Requirements Status](https://requires.io/github/data61/clkhash/requirements.svg?branch=master)](https://requires.io/github/data61/clkhash/requirements/?branch=master)
[![Downloads](https://pepy.tech/badge/clkhash)](https://pepy.tech/project/clkhash)

## Installation

Install clkhash with all dependencies using pip:

    pip install clkhash


## Documentation

[https://clkhash.readthedocs.io](https://clkhash.readthedocs.io/en/latest/)


## clkhash api

To hash a CSV file of entities using the default schema:

```python
from clkhash import clk, randomnames
fake_pii_schema = randomnames.NameList.SCHEMA
clks = clk.generate_clk_from_csv(open('fake-pii-out.csv','r'), 'secret', fake_pii_schema)
```

## Citing

Clkhash, and the wider Anonlink project is designed, developed and supported by 
`CSIRO's Data61 <https://www.data61.csiro.au/>`__. If you use any part of this library in your research, please 
cite it using the following BibTex entry::

    @misc{Anonlink,
      author = {CSIRO's Data61},
      title = {Anonlink Private Record Linkage System},
      year = {2017},
      publisher = {GitHub},
      journal = {GitHub Repository},
      howpublished = {\url{https://github.com/data61/clkhash}},
    }
