void setBuildStatus(String message, String state) {
  step([
    $class: "GitHubCommitStatusSetter",
    reposSource: [$class: "ManuallyEnteredRepositorySource", url: "https://github.com/n1analytics/clkhash"],
    contextSource: [$class: 'ManuallyEnteredCommitContextSource', context: 'jenkins'],
    statusResultSource: [ $class: "ConditionalStatusResultSource", results: [[$class: "AnyBuildResult", message: message, state: state]] ]
  ]);
}

def build(label, release=false) {
    try {
        def workspace = pwd();
        echo "${label}"
        echo "workspace directory is ${workspace}"
        env.PATH = "${workspace}/env/bin:/usr/bin:${env.PATH}"

        withEnv(["VENV=${workspace}/env"]) {

            sh "test -d ${workspace}/env && rm -rf ${workspace}/env || echo 'no env, skipping cleanup'"

            // The stage below is attempting to get the latest version of our application code.
            // Since this is a multi-branch project the 'checkout scm' command is used. If you're working with a standard
            // pipeline project then you can replace this with the regular 'git url:' pipeline command.
            // The 'checkout scm' command will automatically pull down the code from the appropriate branch that triggered this build.
            checkout scm

            def testsError = null

            try {
              stage('Type') {
              sh """#!/usr/bin/env bash
                    set -xe
                    export PATH="/usr/local/bin:\${PATH}"

                    pip install mypy
                    mypy clkhash --ignore-missing-imports --no-implicit-optional --disallow-untyped-calls
                """
              }

              stage('Test') {

                sh """#!/usr/bin/env bash
                    set -xe

                    # Jenkins logs in as a non-interactive shell, so we don't even have /usr/local/bin in PATH
                    export PATH="/usr/local/bin:\${PATH}"
                    printenv

                    rm -fr build

                    # Check python version
                    python --version

                    # Check tox version
                    tox --version

                    # List all available environments
                    tox -a

                    # Run tox. Perhaps add '--skip-missing-interpreters' so the tests won't fail due to missing interpreters?
                    tox -e py27,py34,py35,py36

                   """

                   junit 'testout.xml'
              }

              stage('Coverage'){

                step([$class: 'CoberturaPublisher', coberturaReportFile: 'coverage.xml'])

              }

              stage('Release') {
                if (release) {
                    // Build a distribution wheel on a virtual environment based on python 3.5
                    sh """
                        python3.5 -m venv --clear ${VENV}

                        ${VENV}/bin/python ${VENV}/bin/pip install --upgrade pip setuptools wheel

                        ${VENV}/bin/python setup.py bdist_wheel
                    """

                    // archive the released wheel
                    archiveArtifacts artifacts: "dist/clkhash-*.whl"
                }
              }
            }
            catch (err) {
                testsError = err
                currentBuild.result = 'FAILURE'
                setBuildStatus("Build failed", "FAILURE");
            }
            finally {
                if (testsError) {
                    throw testsError
                }
            }
        }

    } finally {
        deleteDir()
    }
    setBuildStatus("Tests Passed", "SUCCESS");
}

node('GPU 1') {

    if (env.BRANCH_NAME == 'master') {
        build('GPU 1', true)
    } else {
        // We now release from every branch
        build('GPU 1', true)
    }
}
