# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from flask import Blueprint, render_template, session, redirect, url_for
import time


from ...modules import config, database
from ...modules.cache import cache
from ...modules.forms import LoginPW, BaseForm, StringField, BooleanField, IntegerField, SelectField, FieldList, FormField, validators
from ...utils import create_parameter_dict

from .. import components_loaded
if 'BoA_online' in components_loaded:
    from .. import BoA_online

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
    filter_contribution = SelectField('filter contribution:', choices=[('all','all'), ('talk','Talk'), ('poster', 'Poster')], default='all')
    filter_submitted = SelectField('filter submitted:', choices=[('all','all'), ('yes','yes'), ('no', 'no')], default='all')

    filter_text = StringField('Search for')
    filter_field = SelectField('in Field', choices=[('all', 'all'), ('participant_id', 'ID'), ('label', 'Label'), ('participant', 'Participant'), ('title', 'Title')], default='all')

    sort_by = SelectField('sort by', choices=[('participant_id', 'ID'), ('label', 'Label'), ('participant', 'Participant'), ('title', 'Title'), ('category', 'Category')], default='label')
    sort_reverse =  BooleanField('reverse order')

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

    para = create_parameter_dict()

    # create database session
    db_session = database.create_session()

    # get session_choices and create forms
    session_choices = [('-1', '(no session)')]
    for s in db_session.query(database.Session):
        if s.time_slot:
            label = '{} ({})'.format(s.name, s.time_slot)
        else:
            label = s.name
        session_choices.append((str(s.ID), label))

    AbstractForm = Abstract.append_field('session', SelectField('Session', choices=session_choices))
    AbstractsForm = Abstracts.append_field('abstracts', FieldList(FormField(AbstractForm)))
    form = AbstractsForm()

    # update on submit
    if action == 'save':
        if form.validate_on_submit() and form.abstracts:

            # check for duplicate labels
            labels_new = [f.Label.data for f in form.abstracts if f.Label.data]
            abstracts_unchanged = db_session.query(database.Abstract).filter(
                ~database.Abstract.participant_id.in_([f.ID.data for f in form.abstracts]))
            labels_remain = [a.label for a in abstracts_unchanged if a.label]

            if len(labels_new + labels_remain) != len(set(labels_new + labels_remain)):
                form.errors['duplicate labels'] = True
                return render_template('manage_abstracts.html', form=form, **para)

            # clear BoA cache
            if 'BoA_online' in components_loaded:
                cache.delete_memoized(BoA_online.abstract_list)
                cache.delete_memoized(BoA_online.TOC)

            # FieldList wants us to use pop_entry()
            # but we need some freedom in which order we deal with the abstract entries
            # so we first move all subforms in a new list
            subforms = []
            while form.abstracts:
               subforms.append(form.abstracts.pop_entry())

            # get all data
            while subforms:

                try:
                    # first: check for abstracts with empty labels
                    form_abstract = next(f for f in subforms if not f.Label.data)
                except StopIteration:
                    # next: find abstracts whose new label is currently not in database
                    labels_current = db_session.query(database.Abstract.label).distinct().all()
                    form_abstract = next(f for f in subforms if not f.Label.data in labels_current)

                # update abstract in database
                with db_session.no_autoflush:

                    ID = form_abstract.ID.data
                    db_abstract = db_session.query(database.Abstract).get(ID)
                    if not db_abstract:
                        app.logger.warning('manage abstracts: ID not found: ' + ID)
                        continue

                    db_abstract.participant.contribution = form_abstract.contribution.data
                    db_abstract.label = form_abstract.Label.data if form_abstract.Label.data else None
                    db_abstract.time_slot = form_abstract.time_slot.data
                    db_abstract.category = form_abstract.category.data
                    session_id = form_abstract.session.data
                    if session_id == '-1':
                        db_abstract.session = None
                    else:
                        db_abstract.session = db_session.query(database.Session).get(session_id)

                # remove from FieldList
                subforms.remove(form_abstract)

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
        form_abstract.session = abstract.session.ID if abstract.session else '-1'
        form.abstracts.append_entry(form_abstract)

    db_session.close()

    # view page
    return render_template('manage_abstracts.html', form=form, **para)
