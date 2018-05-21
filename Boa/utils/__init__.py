# -*- coding: utf-8 -*-
from codecs import open
import os
from subprocess import Popen

from ..modules import config, database
from ..modules.Email import render_mail

from .contributions import *
from .database import *
from .forms import *
from .registration import *
from .submission import *

def create_parameter_dict(**kwargs):
    """Parameters available for all templates."""
    para = {}
    for key, value in config.conference.__dict__.items():
        para[key] = value
    para['institute_presets'] = config.institute_presets
    para['default_country_id'] = config.forms.default_country_id
    for kw, arg in kwargs.items():
        para[kw] = arg
    return para

def get_dict_from_list(lst, key, value):
    for dic in lst:
        if dic[key] == value:
            return dic
    raise ValueError

## nocache decorator
## code from: http://arusahni.net/blog/2014/03/flask-nocache.html

from functools import wraps, update_wrapper
from datetime import datetime
from flask import make_response

def nocache(view):
    @wraps(view)
    def no_cache(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers['Last-Modified'] = datetime.now()
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response

    return update_wrapper(no_cache, view)

## create invoices
from time import localtime
def create_invoice(ID):
    db_session = database.create_session()
    participant = db_session.query(database.Participant).get(ID)
    assert participant.invoice_number, 'No invoice number set'

    # set parameters
    para = {
        'firstname' : participant.firstname,
        'lastname' : participant.lastname,
        'title' : participant.title,
        'institute' : participant.institute,
        'department' : participant.department,
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
