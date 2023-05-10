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

import sys
import os
import re

from math import ceil

import configparser

import yaml

from .util import get_files
from .util import load_spec

from .defaults import *

from .savedsearches import _savedsearch
from .eventtypes import _event
from .macros import _macro
from .lookups import _static_lookup
from .sourcetype import _sourcetype

class SplunkGen:
    def __init__(self, appname=None, version=None, skel=None):
        self.app = {
            'app.conf': configparser.ConfigParser(interpolation=None),
            'props.conf': configparser.ConfigParser(interpolation=None),
            'eventtypes.conf': configparser.ConfigParser(interpolation=None),
            'tags.conf': configparser.ConfigParser(interpolation=None),
            'savedsearches.conf': configparser.ConfigParser(interpolation=None),
            'transforms.conf': configparser.ConfigParser(interpolation=None),
            'macros.conf': configparser.ConfigParser(interpolation=None)
        }
        for k,v in self.app.items():
            v.optionxform=str
            if skel:
                v.read(os.path.join(skel, 'default', k))

        # Create a barebones app.conf
        appconf = {
            'install': {
                'is_configured': 0
            },
            'package': {
                'check_for_updates': 'false'
            },
            'launcher': {
                'version': version or DEFAULT_VERSION
            },
            'ui': {
                'label': appname or DEFAULT_APPNAME
            }
        }
        for section in self.app['app.conf'].sections():
            appconf[section] = dict(appconf.get(section,{}), **dict(self.app['app.conf'][section].items()))

        self.app['app.conf'].read_dict(appconf)

    # skip_searches = False
    # alert_searches = False
    def load_all(self, sourcedirs: list[str], recursive: dict = True, spec: dict = {}, **kwargs) -> None:
        for src in sourcedirs:
            for k in self.app.keys():
                if os.path.exists(os.path.join(src, k)):
                    spec[k] = load_spec(os.path.join(src, k))

            for entry in os.listdir(src):
                if os.path.isdir(os.path.join(src,entry)) and recursive:
                    self.load_all([os.path.join(src,entry)], recursive=recursive, spec=spec, **kwargs)
                else:
                    self.load_file(os.path.join(src,entry), spec=spec, **kwargs)

    def load_file(self, file: str, **kwargs) -> None:
        fname, ext = os.path.splitext(file)
        if ext in ['.yaml','.yml']:
            try:
                for doc in yaml.load_all(open(file, 'r'), Loader=yaml.Loader):
                    self.load_doc(doc, **kwargs)
            except yaml.scanner.ScannerError as e:
                print(f'*** ERROR loading {file} : {e.problem} {e.problem_mark}')
                print('Continuing...')

        elif ext in ['.csv']:
            _static_lookup(self, file)

    def load_doc(self, doc: dict, spec={}, skip_searches: bool = False, alert_searches: bool = None, **kwargs) -> None:
        # It's possible a yaml doc contains both sourcetype and eventtype fields, but it doesn't make
        # conceptual sense so we'll just regard that as undefined behaviour & handle it as a
        # sourcetype document
        if doc.get('sourcetype'):
            _sourcetype(self, doc)
        elif doc.get('eventtype'):
            _event(self, doc)
        elif doc.get('macro'):
            _macro(self, doc)
        elif doc.get('search') and not doc.get('eventtype') and not skip_searches:
            _savedsearch(self, doc, spec=spec.get('savedsearches.conf',{}), alert=alert_searches)

    def write_app(self, dest: str) -> None:
        # write out the files
        out = os.path.join(dest, 'default')
        os.makedirs(out, exist_ok=True) 
        for k,v in self.app.items():
            with open(os.path.join(out, k), 'w+') as f:
                v.write(f)

