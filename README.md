# CLK Hash

<p align="center">
  <img alt="Clkhash Logo" src="./docs/_static/logo.svg" width="250" />
</p>

<div align="center">

[![codecov](https://codecov.io/gh/data61/clkhash/branch/master/graph/badge.svg)](https://codecov.io/gh/data61/clkhash)
[![Documentation Status](https://readthedocs.org/projects/clkhash/badge/?version=latest)](http://clkhash.readthedocs.io/en/latest/?badge=latest)
[![Unit Testing](https://github.com/data61/clkhash/actions/workflows/unittests.yml/badge.svg)](https://github.com/data61/clkhash/actions/workflows/unittests.yml)
[![Typechecking](https://github.com/data61/clkhash/actions/workflows/typechecking.yml/badge.svg)](https://github.com/data61/clkhash/actions/workflows/typechecking.yml)
[![Downloads](https://pepy.tech/badge/clkhash)](https://pepy.tech/project/clkhash)

</div>

**clkhash** is a Python implementation of cryptographic linkage key hashing as described by _Rainer Schnell, Tobias Bachteler, and Jörg Reiher_ in
[A Novel Error-Tolerant Anonymous Linking Code](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3549247).

## Installation

Install clkhash with all dependencies using pip:

    pip install clkhash


## Documentation

[https://clkhash.readthedocs.io](https://clkhash.readthedocs.io/en/latest/)


## Python API

To hash a CSV file of entities using the default schema:

```python
from clkhash import clk, randomnames
fake_pii_schema = randomnames.NameList.SCHEMA
clks = clk.generate_clk_from_csv(open('fake-pii-out.csv','r'), 'secret', fake_pii_schema)
```

## Command Line Interface

See [Anonlink Client](https://github.com/data61/anonlink-client) for a command line interface to clkhash.

## Citing

Clkhash, and the wider Anonlink project is designed, developed and supported by 
[CSIRO's Data61](https://www.data61.csiro.au). If you use any part of this library in your research, please 
cite it using the following BibTex entry::

    @misc{Anonlink,
      author = {CSIRO's Data61},
      title = {Anonlink Private Record Linkage System},
      year = {2017},
      publisher = {GitHub},
      journal = {GitHub Repository},
      howpublished = {\url{https://github.com/data61/clkhash}},
    }
