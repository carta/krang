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

import os

from typing import Mapping

# Handle lookup definitions
# If there is a list of inputs & outputs defined we add them
def _lookup(self, doc, sourcetype: Mapping) -> None:
    for name, lookup in doc.items():
        if lookup.get('lookup'):
            line = lookup['lookup']
        else:
            line = [name]

        inputs = lookup.get('inputs')
        if inputs:
            if type(inputs) == type({}):
                for k, v in inputs.items():
                    if k == v:
                        line.append(k)
                    else:
                        line.append(f'{v} AS {k}')
            elif type(inputs) == type([]):
                line.extend(inputs)

        line.append('OUTPUT')

        # Splunk's default is to output all the fields from a lookup but
        # we may want to handle outputting only specific fields, and also
        # renaming them
        outputs = lookup.get('outputs')
        if outputs:
            if type(outputs) == type({}):
                for k, v in outputs.items():
                    line.append(f'{v} AS {k}')
            if type(outputs) == type([]):
                line.extend(outputs)

        sourcetype[f'LOOKUP-{name}'] = ' '.join(line)

def _static_lookup(self, filename: str) -> None:
    file = os.path.basename(filename)
    lookup, _ = os.path.splitext(file)
    if not self.app['transforms.conf'].has_section(lookup):
        self.app['transforms.conf'].add_section(lookup)
    self.app['transforms.conf'][lookup] = {'filename': file}

