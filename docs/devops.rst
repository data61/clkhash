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
  - run tests as described in the following table,
  - publish the test results,
  - publish the code coverage (on Azure and codecov),
  - publish the artifacts from the build using ``Python 3.7`` (i.e. the wheel for x86 and x64 and the `tar.gz` source distribution).

The build pipeline requires one environment variable provided by Azure environment:

  - `CODECOV_TOKEN` which is used to publish the coverage to codecov.

Most of the complexity is abstracted into the template in `.azurePipeline/wholeBuild.yml`.

Description of what is tested:

==================   ====================  ===============  =========
Python Version       Operating System      Standard pytest  Notebooks
==================   ====================  ===============  =========
pypy3                ubuntu-18.04          Yes              No
------------------   --------------------  ---------------  ---------
3.5                  ubuntu-18.04          Yes              No
3.5                  macos-10.14           Yes              No
3.5                  vs2017-win2016 (x64)  Yes              No
3.5                  vs2017-win2016 (x86)  Yes              No
------------------   --------------------  ---------------  ---------
3.6                  ubuntu-18.04          Yes              No
3.6                  macos-10.14           Yes              Yes
3.6                  vs2017-win2016 (x64)  Yes              No
3.6                  vs2017-win2016 (x86)  Yes              No
------------------   --------------------  ---------------  ---------
3.7                  ubuntu-18.04          Yes              Yes
3.7                  macos-10.14           Yes              Yes
3.7                  vs2017-win2016 (x64)  Yes              No
3.7                  vs2017-win2016 (x86)  Yes              No
------------------   --------------------  ---------------  ---------
3.8                  ubuntu-18.04          Yes              Yes
3.8                  macos-10.14           Yes              Yes
==================   ====================  ===============  =========



Build Artifacts
~~~~~~~~~~~~~~~

A pipeline artifact named **Release** is created by the build pipeline which contains the universal wheels and the source
distributions for x86 and x64 architectures. Other artifacts are created from each build,
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

