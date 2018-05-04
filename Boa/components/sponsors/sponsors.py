# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from flask import Blueprint, render_template, session, redirect, url_for

from ...modules import config
from ...utils import create_parameter_dict

sponsor_list = config.components.sponsors.sponsors
organizers = config.components.sponsors.organizers
blueprint = Blueprint('sponsors', __name__, url_prefix='/sponsors', template_folder='templates')

@blueprint.route('/')
@blueprint.route('/large')
def sponsors():
    para = create_parameter_dict(
        sponsor_list = sponsor_list,
        organizers = organizers,
    )
    return render_template('sponsors_large.html', **para)

@blueprint.route('/small')
def logos():
    return render_template('sponsors_small.html', sponsor_list=sponsor_list)
