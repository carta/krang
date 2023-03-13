#!/usr/bin/env bash

# Copyright 2023 eShares, Inc. dba Carta, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");  you may not
# use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#
# See the License for the specific language governing permissions and
# limitations under the License.


## Defaults: sleep 15s , 20 times ( 5 mins )
secsleep=15
timeoutunits=20

show_help()
{
   echo
   echo "Usage: $0 [-h] [-t timeout] [-s sleep ] -u <username> -p <password> filename"
   echo "options:"
   echo "-u     Splunk AppInspect username"
   echo "-p     Splunk AppInspect password"
   echo "-s     Sleep time (seconds) (default: 15)"
   echo "-t     Number of times to sleep before timeout (default: 20)"
   echo "-h     Print this help."
   echo
}

token=""
report=""

get_token() {
    token=$(curl -k -u ${user}:${pass} https://api.splunk.com/2.0/rest/login/splunk 2>/dev/null | \
                jq -r .data.token | \
                grep -v null)

    if [[ -z $token ]]; then
        echo "Could not login to AppInspect"
        exit 1
    fi
}

get_validation_report() {
    echo "sending ${filename} to Splunk for inspection"
    reqid=$(curl -X POST "https://appinspect.splunk.com/v1/app/validate" \
                    -H "Authorization: Bearer ${token}" \
                    --form "app_package=@\"${filename}\"" 2>/dev/null | \
                jq -r .request_id | grep -v null)
    echo "polling AppInspect for report"
    for timeout in `seq ${timeoutunits}`; do
        status=$(curl "https://appinspect.splunk.com/v1/app/validate/status/${reqid}?included_tags=private_victoria" -H "Authorization: Bearer ${token}" 2>/dev/null | jq -r .status)
        if [[ "${status}" == "SUCCESS" ]]; then
            break;
        fi;
        if [[ "${timeout}" == "${timeoutunits}" ]]; then
            echo "timed out waiting for app validation. RequestID: ${reqid}"
            exit 1;
        fi;
        echo "(attempt ${timeout}/${timeoutunits}) no results yet, sleeping ${secsleep} seconds..."
        sleep $secsleep;
    done
    echo "retrieving report..."
    report=$(curl -H "Authorization: Bearer ${token}" "https://appinspect.splunk.com/v1/app/report/${reqid}" 2>/dev/null )
}

validate() {
    failures=$(echo $report | jq -r '.reports[0].summary.failure')
    errors=$(echo $report | jq -r '.reports[0].summary.errors')
    if [[ $(( $failures + $errors )) > 0 ]]; then
        echo $report > validation_failures.json
        echo "app validation failed: https://appinspect.splunk.com/v1/app/report/${reqid}"
        exit 1;
    else
        echo "Success"
    fi
}

while getopts "hu:p:s:t:" option; do
   case $option in
      h) show_help
         exit;;
      u) user="$OPTARG"
        ;;
      p) pass="$OPTARG"
        ;;
      t) timeoutunits="$OPTARG"
        ;;
      s) secsleep="$OPTARG"
        ;;
   esac
done
shift "$(($OPTIND -1))"

filename=$1

if [[ -z $user || -z $filename ]]; then
    show_help
    exit 1
fi

if [[ -z $pass ]]; then
    echo -n 'Password: '
    read -s pass
    echo
fi

get_token
get_validation_report
validate
