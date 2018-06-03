# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from flask import Blueprint, redirect, render_template, url_for, session, abort, current_app, jsonify
import time

from ...modules import database, config, Email
from ...modules.forms import LoginPW, BaseForm, StringField, BooleanField, IntegerField, SelectField, FieldList, FormField, validators
from ...modules.export.participant import create_invoice
from ...utils import create_parameter_dict, get_ranks, send_confirm_payment_mail

##########################
###  form definitions  ###
##########################

class Participant(BaseForm):

    ID = StringField('ID')
    title = StringField('Title')
    firstname = StringField('First Name')
    lastname = StringField('Last Name')
    institute = StringField('Institute')
    contribution = StringField('Contribution')
    registered = StringField('Registered')
    payment_confirmed = StringField('Payment Confirmed')
    fee = StringField('Fee')
    events = StringField('Event')
    invoice_number = IntegerField('Invoice No.', [validators.Optional()])

    paid = BooleanField('paid')
    send_confirm = BooleanField('send confirmation mail')
    attach_invoice = BooleanField('attach invoice')

class FilterForm(BaseForm):

    btest = StringField('', [validators.AnyOf('')])    # Bot Protection

    filter_paid = SelectField('filter paid:', choices=[('all','all'),('yes','yes'), ('no', 'no')], default='all')
    filter_rank = SelectField('filter rank:', choices=[('all', 'all'),], default='all')

    filter_text = StringField('Search for')
    filter_field = SelectField('in Field', choices=[('all', 'all'), ('ID', 'ID'), ('name', 'Firstname/Lastname'), ('firstname', 'Firstname'), ('lastname', 'Lastname'), ('institute', 'Institute'), ('events', 'Events'), ('contribution', 'Contribution')], default='all')

    sort_by = SelectField('sort by', choices=[('ID', 'ID'), ('firstname', 'Firstname'), ('lastname', 'Lastname'), ('institute', 'Institute'), ('events', 'Events'), ('contribution', 'Contribution'), ('invoice_number', 'Invoice No.'), ('time_registered', 'Registered')], default='time_registered')
    sort_reverse =  BooleanField('reverse order', default='checked')

########################
###  view functions  ###
########################

blueprint = Blueprint('manage_participants', __name__, url_prefix='/manage_participants', template_folder='templates')

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
            return redirect(url_for('manage_participants.show'))
        else:
            #para['login_failed'] = True
            form.password.errors.append('Invalid password.')
            return render_template('manage_participants_login.html', form=form, **para)

    # view login page
    return render_template('manage_participants_login.html', form=form, **para)

@blueprint.route('/')
@blueprint.route('/<action>', methods=['GET', 'POST'])
def show(action=''):

    if not action in ('', 'filter'):
        return abort(404)

    # check if logged in
    if not 'intern' in session:
        return redirect(url_for('manage_participants.login'))

    # build rank choices for SelectField
    rank_choices = [(rank, rank) for rank in get_ranks()]

    form = FilterForm()
    form.filter_rank.choices = [('all', 'all'),] + rank_choices
    para = create_parameter_dict()

    # create database session
    db_session = database.create_session()

    # get list of participants
    participants = db_session.query(database.Participant)\
        .filter(~database.Participant.rank.in_(config.registration.ranks_hidden))

    # apply filters
    if form.filter_paid.data == 'yes':
        participants = participants.filter(database.Participant.paid)
    elif form.filter_paid.data == 'no':
        participants = participants.filter(database.Participant.paid==False)

    if form.filter_rank.data != 'all':
         participants = participants.filter(database.Participant.rank == form.filter_rank.data)

    if form.filter_text.data:
        if form.filter_field.data == 'all':
            fields = [c[0] for c in form.filter_field.choices]
            fields.remove('all')
            fields.remove('name')
            participants = participants.filter(database.or_( *[ database.func.lower(getattr(database.Participant, field)).contains(database.func.lower(form.filter_text.data)) for field in fields ] + [ database.func.lower(database.Participant.institute).contains(database.func.lower(form.filter_text.data)) ] ))
        elif form.filter_field.data == 'name':
            participants = participants.filter(database.or_(
                database.func.lower(database.Participant.firstname).contains(database.func.lower(form.filter_text.data)),
                database.func.lower(database.Participant.lastname).contains(database.func.lower(form.filter_text.data))
            ))
        else:
            participants = participants.filter(database.func.lower(getattr(database.Participant, form.filter_field.data)).contains(database.func.lower(form.filter_text.data)))

    # sort
    if form.sort_reverse.data:
        participants = participants.order_by(getattr(database.Participant, form.sort_by.data).desc())
    else:
        participants = participants.order_by(getattr(database.Participant, form.sort_by.data))

    # convert to dictionaries
    para['participants'] = []
    for p in participants:
        d = {
            'id' : p.ID,
            'name' : p.fullnamel,
            'institute' : p.institute,
            'rank' : p.rank,
            'events' : p.events,
            'contribution' : p.contribution,
            'registered' : time.strftime('%d/%m/%Y', time.localtime(p.time_registered)),
            'paid' : p.paid,
            'payment_confirmed' : '',
            'fee' : config.calc_fee(p),
            'invoice_no' : p.invoice_number,
            }
        if p.payment_confirmed:
            d['payment_confirmed'] = time.strftime('%d/%m/%Y', time.localtime(p.payment_confirmed))
        para['participants'].append(d)

    db_session.close()

    # view page
    return render_template('manage_participants.html', form=form, **para)

@blueprint.route('/edit/<ID>')
def edit(ID):
    """Return form to edit participant via AJAX."""

    # check if logged in
    if not 'intern' in session:
        return abort(401)   # Unauthorized

    # get participant
    db_session = database.create_session()
    participant = db_session.query(database.Participant).get(ID)
    if not participant:
        current_app.logger.warning('manage participants (edit): ID not found: ' + ID)

    # create and populate form
    rank_choices = [(rank, rank) for rank in get_ranks()]
    ParticipantForm = Participant.append_field('rank', SelectField('rank', choices=rank_choices))
    form = ParticipantForm(
        ID = participant.ID,
        title = participant.title,
        firstname = participant.firstname,
        lastname = participant.lastname,
        institute = participant.institute,
        contribution = participant.contribution,
        registered = time.strftime('%d/%m/%Y', time.localtime(participant.time_registered)),
        confirmed = time.strftime('%d/%m/%Y', time.localtime(participant.payment_confirmed)),
        paid = participant.paid,
        rank = participant.rank,
        events = participant.events,
        invoice_number = participant.invoice_number,
        fee = config.calc_fee(participant),
        send_confirm = session.get('send_confirm', True),
        attach_invoice = session.get('attach_invoice', True),
        )

    if participant.payment_confirmed:
        form.payment_confirmed.data = time.strftime('%d/%m/%Y', time.localtime(participant.payment_confirmed))

    return render_template('participant_modal.html', form=form)

@blueprint.route('/save/', methods=['POST'])
def save():
    """Save participant using AJAX."""

    # check if logged in
    if not 'intern' in session:
        return abort(401)   # Unauthorized

    # create and populate form
    rank_choices = [(rank, rank) for rank in get_ranks()]
    ParticipantForm = Participant.append_field('rank', SelectField('rank', choices=rank_choices))
    form = ParticipantForm()

    # store settings in session cookie
    session['send_confirm'] = form.send_confirm.data
    session['attach_invoice'] = form.attach_invoice.data

    # get participant
    db_session = database.create_session()
    participant = db_session.query(database.Participant).get(form.ID.data)
    if not participant:
        current_app.logger.warning('manage participants (save): ID not found: ' + form.ID.data)
        db_session.close()
        return abort(400)   # Bad Request

    # save to database
    participant.title = form.title.data
    participant.firstname = form.firstname.data
    participant.lastname = form.lastname.data
    participant.institute = form.institute.data
    participant.contribution = form.contribution.data
    participant.paid = form.paid.data
    participant.rank = form.rank.data
    participant.contribution = form.contribution.data.strip()
    participant.events = form.events.data.strip().replace(' ','')
    participant.invoice_number = form.invoice_number.data

    if participant.paid and not participant.invoice_number:
        invoice_no = db_session.query(database.Participant)\
            .order_by(database.Participant.invoice_number.desc()).first().invoice_number
        if not invoice_no: invoice_no = 0
        participant.invoice_number = invoice_no + 1

    if participant.paid and not participant.payment_confirmed:
        participant.payment_confirmed = time.time()
        if session['send_confirm']:
            _para = create_parameter_dict(participant=participant)
            if session['attach_invoice']:
                fname = create_invoice(participant.ID)
                send_confirm_payment_mail(_para, attachments=[fname,])
            else:
                send_confirm_payment_mail(_para)

    try:
        db_session.commit()
    except:
        db_session.rollback()
        db_session.close()
        raise

    data = jsonify(
        id = participant.ID,
        name = participant.fullnamel,
        institute = participant.institute,
        rank = participant.rank,
        events = participant.events,
        contribution = participant.contribution,
        paid = participant.paid,
        payment_confirmed = time.strftime('%d/%m/%Y', time.localtime(participant.payment_confirmed)),
        invoice_no = participant.invoice_number,
        )
    db_session.close()

    return data
