# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from flask import Blueprint, redirect, render_template, url_for, session
import time

from ...modules import database, config
from ...modules.forms import LoginPW, BaseForm, StringField, BooleanField, IntegerField, SelectField, FieldList, FormField, validators
from ...utils import create_parameter_dict

##########################
###  form definitions  ###
##########################

class Session(BaseForm):

    ID = StringField('ID')
    namefield = StringField('Name')
    time_slot = StringField('Time')

class Sessions(BaseForm):

    sort_by = SelectField('sort by', choices=[('ID', 'ID'), ('name', 'Name'), ('time_slot', 'Time')], default='ID')
    sessions = FieldList(FormField(Session))

########################
###  view functions  ###
########################

blueprint = Blueprint('manage_sessions', __name__, url_prefix='/manage_sessions', template_folder='templates')

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
            return redirect(url_for('manage_sessions.show'))
        else:
            #para['login_failed'] = True
            form.password.errors.append('Invalid password.')
            return render_template('manage_sessions_login.html', form=form, **para)

    # view login page
    return render_template('manage_sessions_login.html', form=form, **para)

@blueprint.route('/', methods=['GET', 'POST'])
@blueprint.route('/<action>', methods=['GET', 'POST'])
@blueprint.route('/<action>/<int:ID>', methods=['GET', 'POST'])
def show(action='', ID=None):

    # check if logged in
    if not 'intern' in session:
        return redirect(url_for('manage_sessions.login'))

    form = Sessions()
    para = create_parameter_dict()

    # create database session
    db_session = database.create_session()

    # update on submit
    if action == 'save':
        if form.validate_on_submit():

            # get data
            while form.sessions:

                form_session = form.sessions.pop_entry()
                ID = form_session.ID.data
                print(ID)
                session_ = db_session.query(database.Session).get(ID)
                if not session_:
                    continue
                print(form_session.namefield.data, form_session.time_slot.data)
                session_.name = form_session.namefield.data
                session_.time_slot = form_session.time_slot.data

                # save changes to database
                try:
                    db_session.commit()
                except:
                    db_session.rollback()
                    raise
                finally:
                    db_session.close()

    # add a new session
    elif action == 'add':
        db_session.add(database.Session())

        # save changes to database
        try:
            db_session.commit()
        except:
            db_session.rollback()
            raise
        finally:
            db_session.close()

    # delete a session
    elif action == 'delete':
        if ID is not None:
            session_ = db_session.query(database.Session).get(ID)
            if session_:
                db_session.delete(session_)
                # save changes to database
                try:
                    db_session.commit()
                except:
                    db_session.rollback()
                    db_session.close()
                    raise

    # empty form list
    while form.sessions:
        form.sessions.pop_entry()

    # prepare new list of participants
    sessions = db_session.query(database.Session)

     # sort
    sessions = sessions.order_by(getattr(database.Session, form.sort_by.data))

    # populate form
    for session_ in sessions:
        session_form = Session()
        session_form.ID = session_.ID
        session_form.namefield = session_.name
        session_form.time_slot = session_.time_slot
        form.sessions.append_entry(session_form)

    db_session.close()

    # view page
    return render_template('manage_sessions.html', form=form, **para)
