void setBuildStatus(String message, String state) {
  step([
    $class: "GitHubCommitStatusSetter",
    statusResultSource: [ $class: "ConditionalStatusResultSource", results: [[$class: "AnyBuildResult", message: message, state: state]] ]
  ]);
}

node('GPU 1') {

    stage('Test') {
        try {
            def workspace = pwd();
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

                        tox --version

                        tox --showconfig

                        tox -a -v

                        tox -e py36 --develop -v

                        cat ${PATH}/.tox/log/tox-0.log

                       """
                }
                catch(err) {
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

}