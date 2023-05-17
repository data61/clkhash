Tutorials
=========

The *clkhash* library can be used via the Python API. For a command line interface to ``clkhash``
see `anonlink-client <https://github.com/data61/anonlink-client>`_.

The tutorial `tutorial_api.ipynb` shows an example linkage workflow.

With linkage schema version 3.0 *clkhash* introduced different comparison techniques for feature values.
They are described in the tutorial `tutorial_comparisons.ipynb`.


running the tutorials
^^^^^^^^^^^^^^^^^^^^^

The notebooks can run online using binder.

.. image:: https://mybinder.org/badge_logo.svg
  :target: https://mybinder.org/v2/gh/data61/clkhash/main?filepath=docs


You can download the tutorials from `github <https://github.com/data61/clkhash/tree/main/docs>`_.
The dependencies are listed in `doc-requirements.txt`. Install and start Jupyter from the ``docs``
directory::

    pip install -r doc-requirements.txt
    python -m jupyter lab


Finally you can view a static version of the tutorials here.


.. toctree::
   :maxdepth: 1

   tutorial_api.ipynb
   tutorial_comparisons.ipynb