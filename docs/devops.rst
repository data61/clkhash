Devops
===========

Azure Pipeline
--------------

``clkhash`` is automatically built and tested using Azure Pipeline
 for Windows environment, in the project `Anonlink <https://dev.azure.com/data61/Anonlink>`

Two pipelines are available:
  - `Build pipeline <https://dev.azure.com/data61/Anonlink/_build?definitionId=2>`,
  - `Release pipeline <https://dev.azure.com/data61/Anonlink/_release?definitionId=1>`.

The build pipeline is described by the script `azurePipeline.yml`
which is using resources from the folder `.azurePipeline`.
Mainly, a number of builds and tests are started for different
version of python and system architecture. 
Only the packages created with ``Python 3.7`` and the ``x86``
architecture are then published (in Azure).

The build pipeline is triggered for every pushes on the master branch,
for every tagged commit, and for every pushes part of a pull
request. We are not building on every push and
pull requests not to build twice the same code. For every tagged commit,
the build pipeline will also add the Azure tag `Automated` which will trigger
automatically the release pipeline.

The build pipeline does:

  - install the requirements,
  - package ``clkhash``,
  - run `pytest` (including all the CLI tests and the test requiring a deployed entity service at `https://testing.es.data61.xyz`),
  - run `mypy` for type checking only a chosen version of Python (currently 3.7)
  - run `pytest` to test the notebooks available in the documentation (on Windows, will not install `anonlink` and will run all the tutorials in the file `docs/list__tutorials_without_anonlink.txt`, on other platform, will install `anonlink` and run all the tutorials.)
  - publish the test results,
  - publish the code coverage (on Azure and codecov),
  - publish the artifacts from the build using ``Python 3.7`` with a ``x86`` architecture (i.e. a whl, a tar.gz and an exe).

The build pipeline requires one environment variable provided by Azure environment:

 - `CODECOV_TOKEN` which is used to publish the coverage to codecov.


The release pipeline can either be triggered manually, or automatically from
a successful build on master where the build is tagged `Automated`
(i.e. if the commit is tagged, cf previous paragraph). 

The release pipeline consists of two steps: 
  - asking for a manual confirmation that the artifacts from the triggering build should be released,
  - uses ``twine`` to publish the artifacts.

The release pipeline requires two environment variables provided by Azure environment:
 - `PYPI_LOGIN`: login to push an artifact to ``clkhash`` ``Pypi`` repository,
 - `PYPI_PASSWORD`: password to push an artifact to ``clkhash`` ``Pypi`` repository for the user `PYPI_LOGIN`.

