
clkhash: Cryptographic Linkage Key Hashing
==========================================


``clkhash`` is a python implementation of cryptographic linkage key hashing as described by Rainer
Schnell, Tobias Bachteler, and Jörg Reiher in *A Novel Error-Tolerant Anonymous Linking Code* [Schnell2011]_.

Clkhash is Apache 2.0 licensed, supports Python versions 2.7+, 3.4+, and runs on Windows, OSX and Linux.

Install with pip::

    pip install clkhash


.. hint::

   If you are interested in comparing CLK encodings (i.e carrying out record linkage)
   you might want to check out 
   `anonlink <https://github.com/data61/anonlink>`_ and 
   `anonlink-entity-service <https://github.com/data61/anonlink-entity-service>`__
   - our Python library and REST service for computing
   similarity scores, and matching between sets of cryptographic linkage keys.


Table of Contents
-----------------

.. toctree::
   :maxdepth: 1

   tutorials
   cli
   schema
   development
   rest_client
   references

External Links
--------------

* `clkhash on Github <https://github.com/data61/clkhash/>`_
* `clkhash on PyPi <https://pypi.org/project/clkhash/>`_


Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
