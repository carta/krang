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

import urllib.parse

from typing import Mapping

from .fields import _fields, _aliases
from .lookups import _lookup


def _sourcetype(self, doc: Mapping) -> None:
    name = doc['sourcetype']
    if not self.app['props.conf'].has_section(name):
        self.app['props.conf'].add_section(name)

    # Fields are either eval, extract or aliases
    if doc.get('fields'):
        _fields(self, doc['fields'], self.app['props.conf'][name])

    # aliases are special since we only need to define one sourcetype property
    if doc.get('aliases'):
        _aliases(self, doc['aliases'], self.app['props.conf'][name])

    # automatic lookups for this sourcetype 
    if doc.get('lookups'):
        _lookup(self, doc['lookups'], self.app['props.conf'][name])

    if doc.get('tags'):
        tagname = urllib.parse.quote(name.replace('"',''))
        if not self.app['tags.conf'].has_section(f'sourcetype={tagname}'):
            self.app['tags.conf'].add_section(f'sourcetype={tagname}')
        for tag in doc['tags']:
            self.app['tags.conf'][f'sourcetype={tagname}'][tag] = 'enabled'
