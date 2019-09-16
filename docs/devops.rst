Devops
===========

Azure Pipeline
--------------

``clkhash`` is automatically built and tested using Azure Pipeline
 for Windows environment, in the project `Anonlink <https://dev.azure.com/data61/Anonlink>`

Two pipelines are available:
  - `Build pipeline <https://dev.azure.com/data61/Anonlink/_build?definitionId=2>`,
  - `Release pipeline <https://dev.azure.com/data61/Anonlink/_release?definitionId=1>`.


Build Pipeline
~~~~~~~~~~~~~~

The build pipeline is described by the script `azurePipeline.yml`
which is using template resources from the folder `.azurePipeline`.

There are 3 top level stages in the build pipeline:

- *Static Checks* - runs `mypy` typechecking over the codebase. Also adds a Azure DevOps tag `"Automated"`
  if the build was triggered by a Git tag.
- *Unit tests* - A template expands out into a number of builds and tests for different
  version of python and system architecture.
- *Packaging* - Pulls together the created files into a single release artifact.

The *Build & Test* job does:

  - install the requirements,
  - package ``clkhash``,
  - run `pytest` (including all the CLI tests and the test requiring a deployed entity service at `https://testing.es.data61.xyz`),
  - run `pytest` to test the notebooks available in the documentation (on Windows, will not install `anonlink` and will run all the tutorials in the file `docs/list__tutorials_without_anonlink.txt`, on other platform, will install `anonlink` and run all the tutorials.)
  - publish the test results,
  - publish the code coverage (on Azure and codecov),
  - publish the artifacts from the build using ``Python 3.7`` (i.e. the wheel, the sdist `tar.gz` and an exe for x86 and x64).

The build pipeline requires one environment variable provided by Azure environment:

 - `CODECOV_TOKEN` which is used to publish the coverage to codecov.

Most of the complexity is abstracted into the template in `.azurePipeline/wholeBuild.yml`.

Build Artifacts
~~~~~~~~~~~~~~~

A pipeline artifact named **Release** is created by the build pipeline which contains the universal wheel, source
distribution and Windows executables for x86 and x64 architectures. Other artifacts are created from each build,
including code coverage.


Release Pipeline
~~~~~~~~~~~~~~~~

The release pipeline can either be triggered manually, or automatically from
a successful build on master where the build is tagged `Automated`
(i.e. if the commit is tagged, cf previous paragraph). 

The release pipeline consists of two steps: 
  - asking for a manual confirmation that the artifacts from the triggering build should be released,
  - uses ``twine`` to publish the artifacts.

The release pipeline requires two environment variables provided by Azure environment:
 - `PYPI_LOGIN`: login to push an artifact to ``clkhash`` ``Pypi`` repository,
 - `PYPI_PASSWORD`: password to push an artifact to ``clkhash`` ``Pypi`` repository for the user `PYPI_LOGIN`.

