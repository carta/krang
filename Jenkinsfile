pipeline {
    agent any
    environment {
        APPVERSION = "1.0.${BUILD_NUMBER}"
    }
    stages {
        stage('build') {
            steps {
                sh 'make'
            }
        }
        stage('validate') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'splunkbase', passwordVariable: 'PASS', usernameVariable: 'USER')]) {
                    sh 'bash splunkappvalidate.sh -u $USER -p $PASS ${APPNAME}.tgz'
                }
            }
            post {
                failure {
                    sh 'cat validation_failures.json'
                }
            }
        }
        stage('deploy') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'splunkbase', passwordVariable: 'PASS', usernameVariable: 'USER')]) {
                    script {
                        env.APPVALTOK = sh(script: 'curl -k -u ${USER}:${PASS} https://api.splunk.com/2.0/rest/login/splunk | jq -r .data.token | grep -v null', returnStdout: true).trim()
                    }
                }
                withCredentials([string(credentialsId: 'splunk_acs', variable: 'TOKEN')]) {
                  script {
                    sh 'curl -X POST "https://admin.splunk.com/${SPLUNK_STACK}/adminconfig/v2/apps/victoria" \
                        -H "X-Splunk-Authorization: ${APPVALTOK}" \
                        -H "Authorization: Bearer $TOKEN" \
                        -H "ACS-Legal-Ack: Y" \
                        --data-binary "@${APPNAME}.tgz"'
                  }
                }
            }
        }

    }
}
