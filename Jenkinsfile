void setBuildStatus(String message, String state) {
  step([
    $class: "GitHubCommitStatusSetter",
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
                    tox -e py27,py33,py34,py35,py36

                   """

                if (release) {
                    // Build a distribution wheel
                    sh "python setup.py bdist_wheel"

                    // This will be the official release
                    archiveArtifacts artifacts: "dist/clkhash-*.whl"
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
    stage('GPU 1') {
        if (env.BRANCH_NAME == 'master') {
            build('GPU 1', true)
        } else {
            build('GPU 1', false)
        }
    }
}
