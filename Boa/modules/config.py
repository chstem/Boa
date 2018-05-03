# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from builtins import str as text        # Python 2 and 3: convert to unicode

import os
from codecs import open
from time import *

filepath = os.path.dirname(os.path.realpath(__file__))
module_path = os.path.realpath(os.path.join(filepath, '..'))
prefs_default = os.path.join(module_path, 'preferences')

workdir = os.getcwd()
if module_path.startswith(workdir):
    # running in module dir
    is_instance = False
    prefs_instance = ''
    instance_path = os.path.dirname(prefs_default)
else:
    # running in separate instance
    is_instance = True
    prefs_instance = os.path.join(workdir, 'preferences')
    instance_path = workdir

class struct(object):
    pass

# set testmode
TESTMODE = False

# init objects
registration = struct()
submission = struct()
conference = struct()
conference.account = struct()
mail = struct()
database = struct()
forms = struct()
flask = struct()
ID = struct()
paths = struct()

# components
components_dir = os.path.realpath(os.path.realpath(os.path.join(module_path, 'components')))
components = struct()
components.components_list = []
for d in os.listdir(components_dir):
    path = os.path.join(components_dir, d)
    if not os.path.isdir(path):
        continue
    if os.path.isfile(os.path.join(path, '__init__.py')):
        components.components_list.append(d)
        setattr(components, d, struct())

# fallback for calc_fee()
def calc_fee(participant):
    return None

### load preferences

# default config.py
configfile = os.path.join(prefs_default, 'config.py')
with open(configfile, encoding='utf-8') as fd:
    code = compile(fd.read(), configfile, 'exec')
    exec(code, globals(), locals())

# instance config.py
if is_instance:
    configfile = os.path.join(prefs_instance, 'config.py')
    if os.path.isfile(configfile):
        with open(configfile, encoding='utf-8') as fd:
            code = compile(fd.read(), configfile, 'exec')
            exec(code, globals(), locals())

# some sanity checks
assert set(submission.events).issubset(registration.events), 'config.submission.events needs to be a subset of config.registration.events'

# make sure year is a string
conference.year = text(conference.year)

# check submission.talk_deadline
if not submission.deadline_talks:
    submission.deadline_talks = submission.deadline_poster

# check CSRF secret key
if not flask.CSRF_SECRET_KEY:
    flask.CSRF_SECRET_KEY = flask.secret_key

# make paths absolute
paths.BoA = os.path.join(instance_path, paths.BoA)
paths.abstracts = os.path.join(paths.BoA, paths.abstracts)
paths.backup = os.path.join(instance_path, paths.backup)

### load files in preferences/

# title choices
if is_instance and os.path.isfile(os.path.join(prefs_instance, 'titles.txt')):
    fname_titles = os.path.join(prefs_instance, 'titles.txt')
else:
    fname_titles = os.path.join(prefs_default, 'titles.txt')
with open(fname_titles, encoding='utf-8') as fd:
    titles = fd.read().splitlines()

#ä gender choices
if is_instance and os.path.isfile(os.path.join(prefs_instance, 'genders.txt')):
    fname_genders = os.path.join(prefs_instance, 'genders.txt')
else:
    fname_genders = os.path.join(prefs_default, 'genders.txt')
with open(fname_genders, encoding='utf-8') as fd:
    genders = fd.read().splitlines()

#ä IOC country list
with open(os.path.join(prefs_default, 'IOC_country_codes.txt'), encoding='utf-8') as fd:
    data = [ line.split('\t') for line in fd.read().splitlines() ]
    IOC_code = {country:abrev for abrev, country in data}
    countries = sorted(IOC_code.keys())

# institute presets
if is_instance and os.path.isfile(os.path.join(prefs_instance, 'institute_presets.txt')):
    fname_institutes = os.path.join(prefs_instance, 'institute_presets.txt')
else:
    fname_institutes = os.path.join(prefs_default, 'institute_presets.txt')
with open(fname_institutes, encoding='utf-8') as fd:
    # read file and chunk data
    data = fd.read().splitlines()
    institute_presets = [ data[i:i+5] + [countries.index(data[i+5])] for i in range(0, len(data), 7) ]

## abstract categories
categories = {}
for rank in registration.ranks + registration.ranks_invited + registration.ranks_hidden:
    fname = os.path.join(prefs_instance, 'abstract_categories_%s.txt' %rank)
    if not os.path.isfile(fname):
        fname = os.path.join(prefs_instance, 'abstract_categories.txt')
        if not os.path.isfile(fname):
            fname = os.path.join(prefs_default, 'abstract_categories.txt')
    with open(fname, encoding='utf-8') as fd:
        categories[rank] = fd.read().splitlines()

# clean up
del data

### choices for SelectFields
forms.title_choices = [('pls_choose', '(please choose)')] + [ (str(key), title) for key, title in enumerate(titles) ] + [('other', 'other (please enter):')]
forms.gender_choices = [('pls_choose', '(please choose)')] + [ (str(key), gender) for key, gender in enumerate(genders) ]
forms.institute_choices = [('pls_choose', '(please choose)')] + \
    [ (str(key), institute) for key, institute in enumerate([ inst[0] for inst in institute_presets ]) ] + \
    [('other', 'other (please enter):')]
forms.country_choices = [ (str(key), country) for key, country in enumerate(countries) ]
forms.default_country_id = str(countries.index(forms.default_country))
