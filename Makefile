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

ifeq ($(APPNAME),)
APPNAME = GeneratedApp
endif

ifeq ($(APPVERSION),)
VERSION = 1.0.0
else
VERSION = $(APPVERSION)
endif

ifeq ($(SRCDIR),)
SRCDIR = src
endif

ifeq ($(APPSKEL),)
APPSKEL = skel
endif

ifeq ($(LOOKUPDIR),)
LOOKUPDIR = $(SRCDIR)/lookups
endif

BUILD = build
VENV = venv

VENV_BIN=$(VENV)/bin
PYTHON=$(VENV_BIN)/python
SYS_PYTHON = $(or $(shell which python3), $(shell which python))

TAR = $(shell which tar)
RM = $(shell which rm)
CP = $(shell which cp)
MKDIR = $(shell which mkdir)
OS = $(shell uname)

# Hack to deal with busybox not supporting --transform
TAR_IS_BUSYBOX = $(shell tar --help 2>&1 | grep BusyBox | cut -d ' ' -f 1)
ifeq ($(TAR_IS_BUSYBOX),BusyBox)
BUILD = $(APPNAME)
endif

## tar(1) Flags
ifeq ($(OS),Darwin)
TAR_SUB = -s /$(BUILD)/$(APPNAME)/
TARFLAGS = $(TAR_SUB) --disable-copyfile --exclude '.DS_Store'
endif
ifeq ($(OS),Linux)
ifneq ($(TAR_IS_BUSYBOX),BusyBox)
TAR_SUB = --transform s/$(BUILD)/$(APPNAME)/
TARFLAGS = $(TAR_SUB)
endif
endif

## Build Artifacts
APPCONF = $(BUILD)/default/app.conf
PACKAGE = $(DEST)$(APPNAME).tgz
LOOKUPS = $(patsubst $(LOOKUPDIR),$(BUILD)/lookups,$(wildcard $(LOOKUPDIR)/*.csv))

ARTIFACTS = $(APPCONF) $(PACKAGE)

all: $(ARTIFACTS)

.PHONY: all $(APPCONF)

## Environment setup

$(VENV)/pyvenv.cfg:
	$(SYS_PYTHON) -m venv $(VENV)

deps: $(VENV)/pyvenv.cfg
	$(PYTHON) -m pip install -r requirements.txt

.PHONY: deps

## Build

$(BUILD):
	$(MKDIR) -p $(BUILD)
	$(CP) -rf $(APPSKEL)/* $(BUILD)

.PHONY: $(BUILD)

$(BUILD)/lookups: $(BUILD)
	$(MKDIR) -p $(BUILD)/lookups

$(LOOKUPS): $(BUILD)/lookups
	$(CP) $@ $(BUILD)/lookups/

$(APPCONF): deps $(BUILD) $(LOOKUPS)
	$(PYTHON) generate.py -t $(APPSKEL) -v $(VERSION) -n $(APPNAME) -b $(BUILD) $(SRCDIR)

$(PACKAGE): $(APPCONF)
	$(TAR) -zcf $(PACKAGE) $(TARFLAGS) $(BUILD)

## Check

check: lint

lint: deps
	$(VENV_BIN)/yamllint $(SRCDIR)

.PHONY: check lint

## Validate
validate: $(PACKAGE)
ifneq ($(SPLUNK_USER),)
	 ./splunkappvalidate.sh -u $(SPLUNK_USER) -p $(SPLUNK_PASS) $(PACKAGE)
else
	@echo
	@echo '$$SPLUNK_USER not set, cannot validate app'
	@exit 1
endif

.PHONY: validate

## Clean

clean:
	$(RM) -rf $(ARTIFACTS) $(VENV) $(BUILD)

.PHONY: clean
