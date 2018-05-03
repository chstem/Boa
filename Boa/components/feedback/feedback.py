# -*- coding: utf-8 -*-

from __future__ import unicode_literals, division
from flask import Blueprint, render_template, session, redirect, url_for, send_from_directory, abort, current_app

from sqlalchemy import Table, MetaData, Column, Integer, String, UnicodeText, Unicode, Boolean, BigInteger
from sqlalchemy.orm import mapper
from wtforms import StringField, BooleanField, SelectField, RadioField, TextAreaField, validators

from ...modules import config
from ...modules.database import engine, create_session, collation
from ...modules.forms import BaseForm, MultiCheckboxField, LoginPW
from ...utils import create_parameter_dict, nocache

import os, codecs, json
import time

blueprint = Blueprint('feedback', __name__, url_prefix='/feedback', template_folder='templates')

##################
###  settings  ###
##################

surveys = config.components.feedback.surveys
plot_figures = config.components.feedback.plot_figures

if plot_figures:
    # import modules for plotting
    try:
        import matplotlib
        matplotlib.use('svg')
        import matplotlib.pyplot as plt
        from matplotlib.ticker import MultipleLocator
        import math
    except ModuleNotFoundError:
        print('feedback: matplotlib not found, disabling figures')
        plot_figures = False

###################
###  load JSON  ###
###################

# load feedback questions
questions = {}
for survey in surveys:
    filename = os.path.join(config.instance_path, 'preferences', 'feedback', '{}.json'.format(survey))
    if not os.path.isfile(filename):
        filename = os.path.join(config.prefs_default, 'feedback', '{}.json'.format(survey))
    with codecs.open(filename, encoding='utf-8') as fd:
        try:
            qtemp = json.load(fd)
        except ValueError:
            print('Error in %s, please check if valid JSON' %filename)
            raise

    # check keys
    keys = [ question['key'] for question in qtemp if not question['type'] in ('category', 'head') ]
    assert len(keys) == len(set(keys)), 'only unique event keys in activities.json allowed'
    assert not ',' in ''.join(keys), 'invalid character for keys: \',\''

    # add to dict
    questions[survey] = qtemp

#################################
###  Database and Form Model  ###
#################################

# map question type to column
type2col = {
    'bool' : (Boolean, {}),
    'radio' : (String, {'length':100}),
    'radio_int' : (Integer, {}),
    'text' : (Unicode, {'length':5000, 'collation':collation}),
    'text_area' : (UnicodeText, {'length':5000, 'collation':collation}),
    'multi' : (String, {'length':500, 'collation':collation}),
}

metadata = MetaData()
DBtables = {}

## database
for survey in surveys:

    # build columns for table
    columns = [
        Column('id', Integer, primary_key=True),
        Column('time', BigInteger, default=None, nullable=True),
    ]
    for question in questions[survey]:
        if question['type'] in ('category', 'head'):
            continue
        col, kwargs = type2col[question['type']]
        columns.append(Column(question['key'], col(**kwargs)))
        if question['type'] == 'multi' and question['other']:
            col, kwargs = type2col['text']
            columns.append(Column(question['key']+'_other', col(**kwargs)))

    # build table class
    class DBFeedback(object):
        def __init__(self, **kwargs):
            for key, arg in kwargs.items():
                setattr(self, key, arg)

    # map class to table
    mapper(DBFeedback, Table('feedback_'+survey, metadata, *columns))

    # store class
    DBtables[survey] = DBFeedback

## create Forms
Forms = {}
for survey in surveys:

    class FormFeedback(BaseForm):
        btest = StringField('', [validators.AnyOf('')])    # Bot Protection

    for question in questions[survey]:

        if question['type'] in ('category', 'head'):
            continue

        vals = []
        if question['required']:
            vals.append(validators.InputRequired())
        else:
            vals.append(validators.Optional())

        if question['type'] == 'bool':
            FormFeedback = FormFeedback.append_field(question['key'], BooleanField(question['label']))

        elif question['type'] == 'radio':
            FormFeedback = FormFeedback.append_field(question['key'], RadioField(question['label'], vals, choices=[ (c['key'], c['label']) for c in question['choices']]))

        elif question['type'] == 'radio_int':
            FormFeedback = FormFeedback.append_field(question['key'], RadioField(question['label'], vals, choices=[ (i, i) for i in question['choices'] ], coerce=int))

        elif question['type'] == 'text':
            FormFeedback = FormFeedback.append_field(question['key'], StringField(question['label'], vals))

        elif question['type'] == 'text_area':
            FormFeedback = FormFeedback.append_field(question['key'], TextAreaField(question['label'], vals))

        elif question['type'] == 'multi':
            FormFeedback = FormFeedback.append_field(question['key'], MultiCheckboxField(question['label'], vals, choices=[ (c['key'], c['label']) for c in question['choices']]))
            if question['other']:
                label = 'other:' if isinstance(question['other'], bool) else question['other']
                FormFeedback = FormFeedback.append_field(question['key']+'_other', StringField(label))

    Forms[survey] = FormFeedback

########################
###  view functions  ###
########################

# add filter to format numbers
@blueprint.app_template_filter('format')
def filter_format(value):
    if not value:
        return 'n/a'
    else:
        return '%.2f' %value

@blueprint.route('/', methods=['GET', 'POST'])
def main():
    para = create_parameter_dict(surveys=surveys)
    return render_template('feedback_surveys.html', **para)

@blueprint.route('/<survey>/', methods=['GET', 'POST'])
@blueprint.route('/<survey>/<cont>/', methods=['GET', 'POST'])
def feedback(survey, cont=''):

    if not survey in surveys:
        return abort(404)

    form = Forms[survey]()
    para = create_parameter_dict(
        survey=survey,
        surveys=surveys,
        questions=questions[survey],
        submitted=False,
    )

    if form.validate_on_submit():

        db_session = create_session()
        answers = DBtables[survey]()

        for question in questions[survey]:
            if question['type'] in ('category', 'head'):
                continue
            elif question['type'] == 'multi':
                setattr(answers, question['key'], ','.join(form.data[question['key']]))
                if question['other']:
                    setattr(answers, question['key']+'_other', form.data[question['key']+'_other'])
            else:
                setattr(answers, question['key'], form.data[question['key']])
        answers.time = time.time()

        try:
            db_session.add(answers)
            db_session.commit()
        except:
            db_session.rollback()
            db_session.close()
            raise
        db_session.close()
        para['submitted'] = True

        if cont:
            return redirect(url_for('feedback.feedback', survey=cont))

    return render_template('feedback_questions.html', form=form, **para)

@blueprint.route('/<survey>/results/login/', methods=['GET', 'POST'])
def login(survey):

    # logout previous session
    session.pop('intern', None)

    if not config.internal_password:
        return 'Page is currently offline'

    para = create_parameter_dict(survey=survey, login_failed=False)

    # create form
    form = LoginPW()

    # new login
    if form.validate_on_submit():
        pw = form.password.data
        if pw == config.internal_password:
            session['intern'] = True
            return redirect(url_for('feedback.results', survey=survey))
        else:
            form.password.errors.append('Invalid password.')
            return render_template('feedback_results_login.html', form=form, **para)

    # view login survey
    return render_template('feedback_results_login.html', form=form, **para)

@blueprint.route('/<survey>/results/', methods=['GET', 'POST'])
def results(survey):

    if not survey in surveys:
        return abort(404)

    # check if logged in
    if not 'intern' in session:
        return redirect(url_for('feedback.login', survey=survey))

    db_session = create_session()
    answers = db_session.query(DBtables[survey])

    for question in questions[survey]:

        if question['type'] in ('category', 'head'):
            continue

        elif question['type'] == 'multi':
            question['results'] = {}
            for c in question['choices']:
                count = answers.filter(getattr(DBtables[survey], question['key']).contains(c['key'])).count()
                question['results'][c['label']] = count
            if question['other']:
                question['results']['other'] = filter(None, [ getattr(f, question['key']+'_other') for f in answers.all() ])

        elif question['type'] == 'radio':
            question['results'] = {}
            for c in question['choices']:
                count = answers.filter(getattr(DBtables[survey], question['key']) == c['key']).count()
                question['results'][c['label']] = count

        elif question['type'] == 'radio_int':
            question['results'] = {}
            data = []
            for c in question['choices']:
                count = answers.filter(getattr(DBtables[survey], question['key']) == c).count()
                question['results'][c] = count
                data.extend(count*[c])
            question['results']['average'] = average(data)
            question['results']['std'] = std(data)
            question['results']['median'] = median(data)

            if plot_figures:
                plotfig(survey, question)

        else:

            question['results'] = filter(None, [ getattr(f, question['key']) for f in answers.all() ])

    db_session.close()
    para = create_parameter_dict(survey=survey, questions=questions[survey], plot_figures=plot_figures)

    return render_template('feedback_results.html', **para)

@blueprint.route('/figures/<survey>/<key>')
@nocache
def figures(survey, key):
    return send_from_directory(os.path.join(fig_path, survey), key+'.svg')

####################
###  statistics  ###
####################

def average(data):
    if not data:
        return None
    avg = sum(data)/len(data)
    return avg

def std(data):
    if len(data) < 2:
        return None
    c = average(data)
    std2 = sum((x-c)**2 for x in data)
    std = (std2/len(data))**0.5
    return std

def median(data):
    if not data:
        return None
    data.sort()
    i = len(data)//2
    if len(data) % 2:
        median = data[i]
    else:
        median = 0.5*(data[i-1] + data[i])
    return median

def plotfig(survey, question):

    # create figure
    fig = plt.figure()
    ax = plt.gca()

    # set up xgrid
    x0 = question['choices'][0]-1
    xe = question['choices'][-1]+1
    N = 100
    dx = (xe-x0)/(N-1)
    xgrid = [ i*dx+x0 for i in range(N) ]

    values = [question['results'][key] for key in question['choices']]

    # plot bar
    plt.bar(question['choices'], [question['results'][key] for key in question['choices']], align='center', alpha=0.4, edgecolor='w')

    # plot gaussian for average/std
    sigma = question['results']['std']
    mu = question['results']['average']
    if sigma:

        def gauss(x):
            return (max(values)+0.5) * math.exp(-0.5*((x-mu)/sigma)**2)
        plt.plot(xgrid, map(gauss, xgrid), 'r', linewidth=2)
        plt.plot([mu-sigma, mu+sigma], [gauss(mu-sigma),gauss(mu+sigma)], 'r', linewidth=2)
        #plt.arrow(mu-sigma, gauss(mu-sigma), 2*sigma, 0, color='r', linewidth=2, length_includes_head=True)

        plt.plot([mu, mu], [0, gauss(mu)], 'r', linewidth=2)

    # plot line for average
    elif mu:
        plt.axvline(mu, color='red', linewidth=3)

    # add median
    if question['results']['median']:
        plt.axvline(question['results']['median'], color='green', linewidth=3)

    # annotations
    plt.annotate(xy=(0.77,0.95), s='average = ' + filter_format(question['results']['average']), color='red', xycoords='axes fraction')
    plt.annotate(xy=(0.77,0.90), s='st. dev.  = ' + filter_format(question['results']['std']), color='red', xycoords='axes fraction')
    plt.annotate(xy=(0.77,0.85), s='median  = ' + filter_format(question['results']['median']), color='green', xycoords='axes fraction')

    # appearance
    ax.set_xticks(question['choices'])
    ax.yaxis.set_major_locator( MultipleLocator(1.0) )
    plt.xlim(0, max(question['choices'])+1)
    plt.ylim(0, max(values)+1)

    # save figure
    if not os.path.isdir(os.path.join(fig_path, survey)):
        os.makedirs(os.path.join(fig_path, survey))
    plt.savefig(os.path.join(fig_path, survey, question['key']))

    # close figure
    plt.close()
