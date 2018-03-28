
clkhash: Cryptographic Linkage Key Hashing
==========================================


``clkhash`` is a python implementation of cryptographic linkage key hashing as described by Rainer
Schnell, Tobias Bachteler, and Jörg Reiher in *A Novel Error-Tolerant Anonymous Linking Code* [Schnell2011]_.

Clkhash is Apache 2.0 licensed, supports Python versions 2.7+, 3.4+, and runs on Windows, OSX and Linux.

Install with pip::

    pip install clkhash


.. hint::

   If you are interested in comparing CLKs (i.e carrying out record linkage) you might want to check
   out `anonlink <https://github.com/n1analytics/anonlink>`_ - our Python library for computing
   similarity scores, and best guess matches between two sets of cryptographic linkage keys.


Table of Contents
-----------------

.. toctree::
   :maxdepth: 1

   tutorial.ipynb
   cli
   schema
   development
   references

External Links
--------------

* `clkhash on Github <https://github.com/n1analytics/clkhash/>`_
* `clkhash on PyPi <https://pypi.org/project/clkhash/>`_


Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
