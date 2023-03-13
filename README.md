# KRANG: Knowledge, Reports, Alerts & Normalization Generator

A utility to generate a Splunk knowledge & alerting app from YAML declarations

## Usage

`generate.py` will generate an application and takes several arguments, found with the `--help` metaargument

YAML files and .csv static lookups are placed in a source directory ( default /src ) with a format described below and processed in to relevant Splunk .conf stanzas.

placing a `savedsearches.conf` file with a `default` stanza in a directory allows extra fields to be applied to saved searches (alert or report) to facilitate custom actions. This template is applied to any searches within that directory and any subdirectories unless overridden by another `savedsearches.conf`. These are not applied to the global savedsearches.conf `default` stanza (as that might cause them to apply to other searches in the app when they are not intended) but are instead added to each individual item

Files that are to be included in the application such as UI elements, app icons, etc are placed in the app skeleton directory ( default skel/ ) and are copied first in to the resulting app, and then appended to by the generator

A Makefile and Jenkinsfile are included for convenience

`make` accepts the following environment variable arguments:
- APPNAME (defaults to GeneratedApp)
- APPVERSION (defaults to 1.0.0 )
- SRCDIR (defaults to src)
- APPSKEL (defaults to skel)
- LOOKUPDIR (defaults to src/lookups)

Jenkinsfile is configured to use the secrets `splunkbase` and `splunk_acs`, for login credentials to splunkbase/splunk.com to run appinspect, and ACS for deployment to a Splunk Cloud stack and the environment variable APPNAME for the name as it appears in Splunk

## Knowledge objects

### Field transforms, extractions & calculation

Fields are defined in Splunk per sourcetype ( see [Splunk's documentation for props.conf](https://docs.splunk.com/Documentation/Splunk/latest/admin/propsconf) ) under the `fields` key

`fields` is optional in a sourcetype document, and contains a key-value mapping with values of string, which are converted to `eval` field calculations. 

A special case of field operations is `aliases`, as an optional top level key pointing to a single level key-value mapping that are converted to a single alias definition

sourcetype documents may contain a `tags` key, pointing to an array of tags to be applied by Splunk to the sourcetype

sourcetype documents may contain a `lookups` key, for automatically applying lookups to a sourcetype. Lookups may contain `inputs` and `outputs`, either as a list (passed to `lookup` unmodified) or a single level key-value mapping (passed to `lookup` as `value AS key`. SPL is somewhat counterintuitive in the order of the `AS` operation)

#### Example:

```
sourcetype: "new_sourcetype"
aliases:
  foo: bar
fields:
  myfield: coalesce(first, second)
lookups:
  thing_to_other_thing:
    inputs:
    - infield
    outputs:
      outfield: realfield
tags:
- mytag
```

This will output a `props.conf` entry:

```
[new_sourcetype]
EVAL-myfield = coalesce(first, second)
FIELDALIAS-Global = bar ASNEW foo
LOOKUP-thing_to_other_thing = thing_to_other_thing infield OUTPUT realfield AS outfield
```

and a tags.conf entry:

```
[sourcetype=new_sourcetype]
mytag = enabled
```
### Lookups

CSV files (files with a `.csv` extension) present in the sources directories will be interpreted as static lookup files and applied to `transforms.conf` without the `.csv` extension

### Events

`eventtype` documents  must include `search` and may optionally include `tags`, pointing to an array of tags to be applied by Splunk to the eventtype

### Macros

a `macro` document contains the `macro` field as the name and a `definition` field as the SPL definition of the macro

## Searches, Reports & Alerts

Search definitions Must at minimum include a `name` and `search` field.

A `savedsearches.conf` file with a `[default]` clause in a directory is used as a template for `savedsearches.conf` clauses for every search in that directory and any child directories. _i.e._, every search clause generated will contain the fields in the `[default]` entry, unless overridden by the yaml file itself.

SplunkGen differentiates between a report and an alert if after applying default configuration ( a local or parent directory `savedsearches.conf` ) and parsing the file if `action` `counttype` or any risk annotation keys are present it is treated as an alert, unless it is explicitly declared not to be so with `alert: false`

#### Scheduling
Search scheduling is declared with top level `cron`, `earliest` and `latest` fields, which default to the values in `DEFAULT_SEARCH_SCHEDULING` in [defaults.py](lib/splunkgen/defaults.py)

### Reports

Reports are searches without alert actions, either in the template or definition. A report will send it's results to a lookup. If the search does not contain an `outputlookup` command SplunkGen will append one, using the search name as the lookup name as a CSV file.

Reports will also add a `transforms.conf` entry for the output, removing the trailing `.csv` file extension. This behaviour can be suppressed by adding a `no_transform: true` field to the document (if for instance the report outputs to a key-value store in another app)

### Alerts

The format is based on Splunk's [ESCU generator tool](https://github.com/splunk/security_content) and files generated by that tool remain compatible.

Alerts may contain a top level `trigger` object containing a relation value as documented by [Splunk savedsearches.conf](https://docs.splunk.com/Documentation/Splunk/latest/admin/savedsearchesconf#Notification_options) as a key to an integer value. Defaults to `greater than: 0`

The `tags` object may contain information relating to risk & Splunk ES correlation searches & notables. Available keys are documented in the `ANNOTATION_KEYS` constant in [util.py](lib/splunkgen/util.py)

Fields available in the `tags` object may be provided at the top-level object

#### Throttle

Splunk allows alerts to be throttled on a single field and this is exposed as a `throttle` object containing `fields` as a list or string scalar to throttle the alert on, and a suppression period, `time`

#### Risk and Notables

Risk-based alerting in ES can be achieved through `risk_score`, `impact`, and `confidence` fields, all of which are optional and can be placed in the `tags` object or at the top level document. Defaults to 100, and `risk_score` is calculated as `impact * confidence / 100` if not explicitly declared.

An `observables` object is used by Splunk to apply risk to specific objects by way of a `risk` alert action and if an observables object is present, SplunkGen will add RBA fields to the final representation

Notables are used in ES as an alert action, and unless suppressed with `notable: false` SplunkGen will generate notable action fields for alerts, with severity the same as the RBA risk score
