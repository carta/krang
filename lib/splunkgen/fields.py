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

from typing import Mapping

# Handle field extractions and evals
def _fields(self, doc: dict, sourcetype: Mapping) -> None:
    for k,v in doc.items():
        if type(v) == type({}):
            # We aren't currently handling transforms, but we could
            if v.get('extraction'):
                sourcetype[f'EXTRACT-{k}'] = v['extraction']
        elif type(v) == type(''):
            sourcetype[f'EVAL-{k}'] = v.replace('\n',' ')

# Handle aliases in to a sourcetype 'Global' alias
def _aliases(self, doc: dict, sourcetype: Mapping):
    sourcetype['FIELDALIAS-Global'] = ' '.join(list(map(lambda x: f'{x[1]} ASNEW {x[0]}', doc.items())))
