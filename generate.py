#! /usr/bin/env python3
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
import argparse

sys.path.append('lib')
from splunkgen import SplunkGen

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', '-n', default='GeneratedApp', help='App name')
    parser.add_argument('--version', '-v', default='1.0.0', help='App version')
    parser.add_argument('--skel', '-t', default='skel', help='App template directory')
    parser.add_argument('--no-recursive', '-r', action='store_false', help='Don\'t traverse source subdirectories')
    parser.add_argument('--build', '-b', default='build', help='Build directory to write .conf files to')
    parser.add_argument('src', default='src', nargs='+', help='Source directories containing yaml files & lookup csv\'s')

    args = parser.parse_args()

    app = SplunkGen(appname=args.name, version=args.version, skel=args.skel)
    app.load_all(args.src, recursive=args.no_recursive)

    app.write_app(args.build)
