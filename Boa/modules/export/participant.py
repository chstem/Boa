# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import codecs
from glob import glob
import json
import os
import re
from shutil import copy
from subprocess import Popen
from time import localtime

from .. import config
from ..database import *

####################################
###  export participant as JSON  ###
####################################

def export_to_json(ID):
    """Export participant from database to JSON."""

    # get participant from database
    db_session = create_session()
    participant = db_session.query(Participant).get(ID)

    if not participant:
        db_session.close()
        return

    # create dict
    data = {
        'Participant':{},
        'Abstract':{},
        'Authors':[],
        'Affiliations':[],
        }

    # Participant
    for key, value in participant.__dict__.items():
        if key.startswith('_'):
            continue
        if key in ('abstract',):
            continue
        data['Participant'][key] = value

    if participant.abstract:

        # Abstract
        for key, value in participant.abstract.__dict__.items():
            if key.startswith('_'):
                continue
            if key in ('authors','affiliations', 'participant_id'):
                continue
            data['Abstract'][key] = value

        # Authors
        for author in participant.abstract.authors:
            data['Authors'].append({})
            for key, value in author.__dict__.items():
                if key.startswith('_'):
                    continue
                if key in ('id', 'abstract_id', 'participant_id'):
                    continue
                data['Authors'][-1][key] = value

        # Affiliations
        for affil in participant.abstract.affiliations:
            data['Affiliations'].append({})
            for key, value in affil.__dict__.items():
                if key.startswith('_'):
                    continue
                if key in ('id', 'abstract_id'):
                    continue
                data['Affiliations'][-1][key] = value

    # store as JSON file
    fname = ID + '.json'
    if not os.path.isdir(config.paths.backup):
        os.mkdir(config.paths.backup)
    with codecs.open(os.path.join(config.paths.backup, fname), 'w', encoding='utf-8') as fd:
        json.dump(data, fd)

    db_session.close()

    # copy figure(s)
    for fname in glob(os.path.join(config.paths.abstracts,ID,'figure.*')):
        ext = fname.rsplit('.', 1)[1].lower()
        copy(fname, os.path.join(config.paths.backup, '%s.%s' %(ID, ext)))

def import_json(ID, change_ID=None):
    """Import participant from a JSON formatted file."""

    # load JSON
    fname = ID + '.json'
    with codecs.open(os.path.join(config.paths.backup, fname), encoding='utf-8') as fd:
        data = json.load(fd)

    # Participant
    participant = Participant(**data['Participant'])

    if change_ID:
        participant.ID = change_ID

    # Abstract
    if data['Abstract']:

        abstract = Abstract(**data['Abstract'])

        authors = []
        for author in data['Authors']:
            authors.append( Author(**author) )

        affiliations = []
        for affil in data['Affiliations']:
            affiliations.append( Affiliation(**affil) )

        abstract.authors = authors
        abstract.affiliations = affiliations
        participant.abstract = abstract

    # add to database
    db_session = create_session()
    try:
        db_session.add(participant)
        db_session.commit()
    except:
        db_session.rollback()
        db_session.close()
        raise

    # restore figure(s)
    for fname in glob(os.path.join(config.paths.backup,ID+'.*')):
        ext = fname.rsplit('.', 1)[1].lower()
        if ext != 'json':
            if not os.path.isdir(os.path.join(config.paths.abstracts,participant.ID)):
                os.mkdir(os.path.join(config.paths.abstracts,participant.ID))
            copy(fname, os.path.join(config.paths.abstracts,participant.ID,'figure.%s' %ext))

    db_session.close()

##################
###  Invoices  ###
##################

def create_invoice(ID):
    db_session = create_session()
    participant = db_session.query(Participant).get(ID)
    assert participant.invoice_number, 'No invoice number set'

    # set parameters
    para = {
        'firstname' : participant.firstname,
        'lastname' : participant.lastname,
        'title' : participant.title,
        'address_line1' : participant.address_line1,
        'address_line2' : participant.address_line2,
        'street' : participant.street,
        'PLZ' : participant.postal_code,
        'city' : participant.city,
        'invoice_no' : participant.invoice_number,
        'tax_no' : participant.tax_number,
        'events' : participant.events,
        'fee' : config.calc_fee(participant),
    }
    for key, value in config.conference.account.__dict__.items():
        para[key] = value
    if config.registration.earlybird:
        para['earlybird'] = localtime(participant.time_registered) <= config.registration.earlybird
    else:
        para['earlybird'] = False
    if config.registration.surcharge:
        para['surcharge'] = localtime() > config.registration.surcharge
    else:
        para['surcharge'] = False

    # create tex file from template
    with open(os.path.join(config.instance_path, 'invoice_template.tex'), encoding='utf-8') as fd:
        template = fd.read()
    if not os.path.isdir(os.path.join(config.instance_path, 'invoices')):
        os.mkdir(os.path.join(config.instance_path, 'invoices'))
    fname = os.path.join(config.instance_path, 'invoices', 'Nr_{:04d}'.format(participant.invoice_number))
    with open(fname+'.tex', 'w', encoding='utf-8') as fd:
        fd.write(template %para)
    db_session.close()

    # run pdflatex
    os.chdir('invoices')
    p = Popen(['pdflatex', fname+'.tex'])
    p.wait()
    os.chdir(config.instance_path)

    # return full filename
    return fname + '.pdf'
