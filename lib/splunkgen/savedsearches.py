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

import json
import re
import os

from .util import ANNOTATION_KEYS
from .defaults import DEFAULT_SEARCH_SCHEDULING

from typing import Iterable, Mapping
from math import ceil

def _savedsearch(self, doc: dict, spec: dict = {}, alert: bool = None) -> None:
    search = spec.copy()

    # In case we haven't set this yet. We do want searches to run
    search['enableSched'] = 1

    alert = doc.get('alert', alert)

    # Alerts have actions, a counttype field, or 'alert.*' fields
    #  reports / lookup generators don't they just write csv files
    if alert is None:
        for k in search.keys():
            if k.startswith('action') or k.startswith('alert') or k == 'counttype':
                alert = True
                break

    # If the spec is unclear, find alert fields in the doc
    if alert is None:
        tagkeys = dict(doc.get('tags',{}), **doc).keys()
        if 'risk_score' in tagkeys or set(tagkeys).intersection(ANNOTATION_KEYS):
            alert = True

    if alert == True:
        search.update(_alert(self, doc))
    else:
        search.update(_report(self, doc))

    # splunk/security_content uses an overly verbose '{"scheduling": {"cron_schedule": ...' format
    # We'll support it, but also a slightly nicer '{"schedule":{"cron": ...' format as well as top level
    # cron, earliest & latest keys

    schedule = doc.get('schedule', doc.get('scheduling',{}))
    cron = schedule.get('cron', schedule.get('cron_schedule', doc.get('cron')))
    if cron:
        search['cron_schedule'] = cron

        earliest = schedule.get('earliest', schedule.get('earliest_time', doc.get('earliest')))
        latest = schedule.get('latest', schedule.get('latest_time', doc.get('latest')))

        if earliest:
            search['dispatch.earliest_time'] = earliest
            if latest:
                search['dispatch.latest_time'] = latest
            else:
                search['dispatch.latest_time'] = 'now'

    if not search.get('cron_schedule'):
        search.update(DEFAULT_SEARCH_SCHEDULING)

    if not self.app['savedsearches.conf'].has_section(doc['name']):
        self.app['savedsearches.conf'].add_section(doc['name'])

    self.app['savedsearches.conf'][doc['name']] = search
   
def _report(self, doc: dict) -> Mapping[str, dict]:
    search = doc['search'].replace('\n',' ')

    # There are cases where we might not want to modify our transforms.conf
    # such as writing to extant k:v stores
    if doc.get('no_transform') == True:
        return {'search': search}

    # need to find out if the search already contains an `| outputlookup` stanza
    # and if so, pull the table/csv name from it.
    table = None
    spl_command = search.split('|')

    for command in spl_command:
        if command.lstrip().startswith('outputlookup'):
            table = command.rstrip().split(' ')[-1]
            break

    # transforms.conf expects a stanza without a .csv and a filename with it
    if table:
        tablename, ext = os.path.splitext(table)
    else:
        # If it doesn't have an outputlookup section we need to add it
        # We're using the name of the saved search
        #
        # Note that if we don't have an `|inputlookup` stanza this table can grow
        # unbounded if append=T so we're going to leave that off and regen the table from
        # scratch.
        #
        # TODO: handle some key fields that we can merge the input & output tables on
        # and modify this to add an |inputlookup | dedup | outputlookup
        r = re.compile('\W')
        tablename = re.sub(r, '_', doc['name'].lower())
        ext = '.csv'
        search += f'| outputlookup {tablename}{ext}'

    if not self.app['transforms.conf'].has_section(tablename):
        self.app['transforms.conf'].add_section(tablename)
    self.app['transforms.conf'][tablename] = {'filename': f'{tablename}{ext}'}

    return {'search': search}

def _alert(self, doc: dict) -> Mapping[str, dict]:
    search = doc['search'].replace('\n',' ')
    ret = {
        'search' : search,
        'counttype': 'number of events'
    }
    # allow setting relation & quantity in savedsearches.conf
    if doc.get('trigger') and isinstance(doc['trigger'], dict):
        relation = list(doc['trigger'].keys())[0]
        ret['relation'] = relation
        ret['quantity'] = doc['trigger'][relation]
    else:
        ret.update({'relation': 'greater than',
                    'quantity': 0})

    # Splunk Security stashes a bunch of things in the `tags` section but there's no reason
    # to not use the top level object, so we'll accept both, overwriting tags with doc keys
    # by merging the tags dict with the doct dict
    tags = dict(doc.get('tags',{}), **doc)

    # risk score relates to the risk index, impact/confidence are fields
    # from correlation searches. Their relationship in the Splunk security_content
    # repo is risk_score = (impact*confidence)/100 but that's a sanity check we don't
    # need, so we won't. But we'll fill in some sane-ish values if only one set is provided
    risk_score = tags.get('risk_score')
    impact = tags.get('impact')
    confidence = tags.get('confidence')

    annotation = {}
    risk_objects = []

    if risk_score or impact:
        if not confidence:
            confidence = 100

        if risk_score and not impact:
            impact = int(risk_score)
        else:
            risk_score = ceil(int(impact) * int(confidence) / 100)
    else:
        # If there's nothing to calculate risk by we can only assume to max it out
        risk_score = 100
        impact = 100
        confidence = 100


    observables = tags.get('observable')
    if observables:
        risk_objects.extend(_addRBA(observables, risk_score))

    # Any risk objects that exist to add to the risk index
    if len(risk_objects) > 0:
        ret['action.risk'] = 1
        ret['action.risk.param._risk'] = json.dumps(risk_objects)
        ret['action.risk.param._risk_score'] = 0

        message = tags.get('message')
        if message:
            ret['action.risk.param._risk_message'] = message.replace('\n', ' ')

    # Any correlation search annotations
    for k in ANNOTATION_KEYS:
        tmp = tags.get(k)
        if tmp:
            annotation[k] = tmp
    
    if len(annotation) > 0:
        # if any of the annotations exist, we'll add to them but if not we don't
        # want to turn a regular search in to a correlation search
        annotation['impact'] = impact
        annotation['confidence'] = confidence
        annotation['observable'] = observables

        ret['action.correlationsearch.enabled'] = 1
        ret['action.correlationsearch.label'] = doc['name']
        ret['action.correlationsearch.annotations'] = json.dumps(annotation)

    # Notables, if not suppressed
    if doc.get('notable', True):
        ret['action.notable'] = 1
        ret['action.notable.param.rule_title'] = doc['name']
        ret['action.notable.param.nes_fields']  = 'user, dest'

        if risk_score < 50:
            severity = 'low'
        elif risk_score >= 80:
            severity = 'high'
        else:
            severity = 'medium'
        ret['action.notable.param.severity'] = severity

        domain = tags.get('security_domain')
        if domain:
            ret['action.notable.param.security_domain'] = domain

    # Scheduling throttle
    throttle = doc.get('throttle')
    if throttle and throttle.get('fields'):
        ret['alert.suppress'] = 1
        ret['alert.suppress.fields'] = ','.join(throttle['fields']) if type(throttle['fields']) is list else throttle['fields']
        ret['alert.suppress.period'] = throttle.get('time', '5m')

    return ret

def _addRBA(observables: dict, risk_score: int) -> Iterable[dict]:
    ret = []

    user_types = {'user', 'username', 'email address'}
    system_types = {'device', 'endpoint', 'hostname', 'ip address'}

    for obj in observables:
        risk_object = {}
        if obj.get('type', '').lower() in user_types:
            risk_object['risk_object_type'] = 'user'
            risk_object['risk_object_field'] = obj['name']
            risk_object['risk_score'] = risk_score

        elif obj.get('type','').lower() in system_types:
            risk_object['risk_object_type'] = 'system'
            risk_object['risk_object_field'] = obj['name']
            risk_object['risk_score'] = risk_score
        else:
            name = obj.get('name')
            if not name:
                continue
            risk_object['threat_object_field'] = name
            risk_object['threat_object_type'] = obj.get('type', 'unknown').lower()
            risk_object['risk_score'] = risk_score

        ret.append(risk_object)

    return ret
