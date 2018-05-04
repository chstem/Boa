# -*- coding: utf-8 -*-

# list of links for managing the web application

from __future__ import unicode_literals
from flask import Blueprint, render_template, url_for, current_app

from .. import components_loaded
from ... import utils

blueprint = Blueprint('tools', __name__, url_prefix='/tools', template_folder='templates')

@blueprint.route('/')
def tools():
    para = utils.create_parameter_dict()

    # core pages
    register_subpages = [(rank, url_for('register', rank=rank)) for rank in utils.get_ranks()]
    register_subpages += [('onsite', url_for('register', rank='onsite'))]
    core_pages = [
        ('Registration', register_subpages),
        ('Abstract Submission', [('Abstract Submission', url_for('abstract_submission'))]),
    ]

    # manage pages
    manage_pages = []
    if 'manage_participants' in components_loaded:
        manage_pages.append(['Participants', url_for('manage_participants.show')])
    if 'manage_abstracts' in components_loaded:
        manage_pages.append(['Abstracts', url_for('manage_abstracts.show')])
    if 'manage_sessions' in components_loaded:
        manage_pages.append(['Sessions', url_for('manage_sessions.show')])

    # remaining components
    components = []
    if 'MassMail' in components_loaded:
        components.append(('component', [('Mass Mail', url_for('MassMail.MassMail'))]))

    para['pages'] = core_pages
    if manage_pages:
        para['pages'] += [('Manage', manage_pages)]
    if components:
        para['pages'] += components

    # put stats at end
    para['pages'] +=  [('Stats', [('Stats', url_for('stats'))])]

    return render_template('tools.html', **para)
