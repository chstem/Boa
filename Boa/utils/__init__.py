# -*- coding: utf-8 -*-
from codecs import open
import os

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
