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
                withCredentials([usernamePassword(credentialsId: 'splunkbase', passwordVariable: 'SPLUNK_PASS', usernameVariable: 'SPLUNK_USER')]) {
                    sh 'make validate'
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
                withCredentials([usernamePassword(credentialsId: 'splunkbase', passwordVariable: 'PASS', usernameVariable: 'USERNAME')]) {
                    script {
                        env.APPVALTOK = sh(script: 'curl -k -u ${USERNAME}:${PASS} https://api.splunk.com/2.0/rest/login/splunk | jq -r .data.token | grep -v null', returnStdout: true).trim()

                    }
                }
                withCredentials([usernamePassword(credentialsId: 'splunk_sa', passwordVariable: 'PASS', usernameVariable: 'USERNAME')]) {
                  script {
                    env.TOKEN = sh(script: ''' curl -X POST -k -u ${USERNAME}:${PASS} "https://admin.splunk.com/${SPLUNK_STACK}/adminconfig/v2/tokens" \
                    -H "Content-Type: application/json" \
                    --data-raw '{
                          "user" : "'"${USERNAME}"'",
                          "audience" : "jenkins",
                          "expiresOn" : "+5m",
                          "type" : "ephemeral"
                    }' | jq -r .token '''
                    , returnStdout: true).trim()

                    env.RESPONSE = sh(script: 'curl -X POST "https://admin.splunk.com/${SPLUNK_STACK}/adminconfig/v2/apps/victoria" \
                        -H "X-Splunk-Authorization: ${APPVALTOK}" \
                        -H "Authorization: Bearer $TOKEN" \
                        -H "ACS-Legal-Ack: Y" \
                        --data-binary "@${APPNAME}.tgz"' \
                        , returnStdout: true).trim()

                    def responseJson = readJSON text: RESPONSE
                    def installStatus = responseJson.status
                    echo "Deployment Status: $installStatus"

                    if(installStatus != "installed") {
                        error ('App Install Failed. Exiting script')
                    }
                  }
                }
            }
        }

    }
}
