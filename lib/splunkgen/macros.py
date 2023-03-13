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

import re

def _macro(self, doc: dict) -> None:
    name = doc['macro']

    # strip out comments, make it all one line, and then strip whitespace
    definition = re.sub(r'#.*', '', doc['definition']).replace('\n',' ').strip()
    args = doc.get('args')

    if args:
        name = f'{name}({len(args)})'

    if not self.app['macros.conf'].has_section(name):
        self.app['macros.conf'].add_section(name)

    self.app['macros.conf'][name] = {'definition': definition, 'enabled':'true'}

    if args:
        self.app['macros.conf'][name]['args'] = ','.join(args)

