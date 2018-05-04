# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from flask import Blueprint, render_template, session, redirect, url_for
import time


from ...modules import database, config
from ...modules.forms import LoginPW, BaseForm, StringField, BooleanField, IntegerField, SelectField, FieldList, FormField, validators
from ...utils import create_parameter_dict

##########################
###  form definitions  ###
##########################

class Abstract(BaseForm):

    ID = StringField('ID')
    Label = StringField('Label')
    time_slot = StringField('Time')
    contribution = StringField('Contribution')
    category = StringField('Category')
    title = StringField('Title')
    participant = StringField('Participant')
    submitted = BooleanField('submitted')

class Abstracts(BaseForm):

    btest = StringField('', [validators.AnyOf('')])    # Bot Protection

    filter_contribution = SelectField('filter contribution:', choices=[('all','all'), ('talk','Talk'), ('poster', 'Poster')], default='all')
    filter_submitted = SelectField('filter submitted:', choices=[('all','all'), ('yes','yes'), ('no', 'no')], default='all')

    filter_text = StringField('Search for')
    filter_field = SelectField('in Field', choices=[('all', 'all'), ('participant_id', 'ID'), ('label', 'Label'), ('participant', 'Participant'), ('title', 'Title')], default='all')

    sort_by = SelectField('sort by', choices=[('participant_id', 'ID'), ('label', 'Label'), ('participant', 'Participant'), ('title', 'Title'), ('category', 'Category')], default='label')
    sort_reverse =  BooleanField('reverse order')

    abstracts = FieldList(FormField(Abstract))

########################
###  view functions  ###
########################

blueprint = Blueprint('manage_abstracts', __name__, url_prefix='/manage_abstracts', template_folder='templates')

@blueprint.route('/login/', methods=['GET', 'POST'])
def login():

    # logout previous session
    if 'intern' in session:
        session.pop('intern', None)

    if not config.internal_password:
        return 'Page is currently offline'

    para = create_parameter_dict(login_failed=False)

    # create form
    form = LoginPW()

    # new login
    if form.validate_on_submit():
        pw = form.password.data
        if pw == config.internal_password:
            session['intern'] = True
            return redirect(url_for('manage_abstracts.show'))
        else:
            #para['login_failed'] = True
            form.password.errors.append('Invalid password.')
            return render_template('manage_abstracts_login.html', form=form, **para)

    # view login page
    return render_template('manage_abstracts_login.html', form=form, **para)

@blueprint.route('/', methods=['GET', 'POST'])
@blueprint.route('/<action>', methods=['GET', 'POST'])
def show(action=''):

    # check if logged in
    if not 'intern' in session:
        return redirect(url_for('manage_abstracts.login'))

    form = Abstracts()
    para = create_parameter_dict()

    # create database session
    db_session = database.create_session()

    # add session field to abstract form
    sessions = [s.name for s in db_session.query(database.Session)]
    session_choices = [('', '')] + [(s, s) for s in sessions]
    print(session_choices)
    AbstractForm = Abstract.append_field('session', SelectField('Options', choices=session_choices))

    # update on submit
    if action == 'save':
        if form.validate_on_submit():

            # get data
            while form.abstracts:
                form_abstract = form.abstracts.pop_entry()
                ID = form_abstract.ID.data
                db_abstract = db_session.query(database.Abstract).get(ID)
                if not db_abstract:
                    app.logger.warning('manage abstracts: ID not found: ' + ID)
                    continue

                db_abstract.participant.contribution = form_abstract.contribution.data
                db_abstract.label = form_abstract.Label.data if form_abstract.Label.data else None
                db_abstract.time_slot = form_abstract.time_slot.data
                db_abstract.category = form_abstract.category.data
                session_name = form_abstract.session.data
                session_ = db_session.query(database.Session).filter(database.Session.name == session_name).one()
                db_abstract.session = session_

                # save changes to database
                try:
                    db_session.commit()
                except:
                    db_session.rollback()
                    raise
                finally:
                    db_session.close()

    # empty form list
    while form.abstracts:
        form.abstracts.pop_entry()

    # prepare new list of abstracts
    abstracts = db_session.query(database.Abstract).join(database.Participant)

    # apply filters
    if form.filter_contribution.data != 'all':
         abstracts = abstracts.filter(database.Participant.contribution == form.filter_contribution.data)

    if form.filter_text.data:
        if form.filter_field.data == 'all':
            fields = [c[0] for c in form.filter_field.choices]
            fields.remove('all')
            fields.remove('participant')
            filters = [database.func.lower(getattr(database.Abstract, field)).contains(database.func.lower(form.filter_text.data)) for field in fields]
            filters.append(database.func.lower(database.Participant.firstname).contains(database.func.lower(form.filter_text.data)))
            filters.append(database.func.lower(database.Participant.lastname).contains(database.func.lower(form.filter_text.data)))
            abstracts = abstracts.filter(database.or_(*filters))
        elif form.filter_field.data == 'participant':
            abstracts = abstracts.filter(database.or_(
                database.func.lower(database.Participant.firstname).contains(database.func.lower(form.filter_text.data)),
                database.func.lower(database.Participant.lastname).contains(database.func.lower(form.filter_text.data))
            ))
        else:
            abstracts = abstracts.filter(database.func.lower(getattr(database.Abstract, form.filter_field.data)).contains(database.func.lower(form.filter_text.data)))

    # sort
    if form.sort_reverse.data:
        abstracts = abstracts.order_by(getattr(database.Abstract, form.sort_by.data).desc())
    else:
        abstracts = abstracts.order_by(getattr(database.Abstract, form.sort_by.data))

    if form.filter_submitted.data == 'yes':
        abstracts = [a for a in abstracts if a.is_submitted]
    elif form.filter_submitted.data == 'no':
        abstracts = [a for a in abstracts if not a.is_submitted]

    # populate form
    for abstract in abstracts:
        form_abstract = AbstractForm()
        form_abstract.ID = abstract.participant.ID
        form_abstract.Label = abstract.label
        form_abstract.time_slot = abstract.time_slot
        form_abstract.contribution = abstract.participant.contribution
        form_abstract.category = abstract.category
        form_abstract.title = abstract.title
        form_abstract.participant = abstract.participant.fullnamel
        form_abstract.submitted = abstract.participant.abstract_submitted
        form_abstract.session = abstract.session.name if abstract.session else ''
        form.abstracts.append_entry(form_abstract)

    db_session.close()

    # view page
    return render_template('manage_abstracts.html', form=form, **para)
