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
import configparser

ANNOTATION_KEYS = { 
                'mitre_attack',
                'kill_chain_phases',
                'cis20',
                'nist', 
                'analytic_story',
                'observable',
                'context',
                'cve',
                'impact',
                'confidence' }

def get_files(src, filetypes=['yaml','yml'], nopath=False):
    ret = []
    if type(filetypes) == str:
        filetypes = [filetypes]
    for file in os.listdir(src):
        fname, ext = os.path.splitext(file)
        if ext != '' and ext[1:] in filetypes:
            if nopath:
                ret.append(file)
            else:
                ret.append(os.path.join(src, file))
    return ret

# configparser has a DEFAULTS section but we don't want to use that
# because some of our savedsearches are going to be alerts and some are
# report generators. So, while this is a somewhat silly way to do this
# it's alright for our purposes
def load_spec(file, section='default'):
    try:
        spec = configparser.ConfigParser(interpolation=None, default_section=section)
        spec.optionxform = str
        spec.read(file)
        return spec.defaults()
    except configparser.Error as e:
        print(f'error in spec file: {e}')
    return {}
