# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from flask import Blueprint, redirect, render_template, url_for, session
import time

from ...modules import database, config, Email
from ...modules.forms import LoginPW, BaseForm, StringField, BooleanField, IntegerField, SelectField, FieldList, FormField, validators
from ...utils import create_parameter_dict, get_ranks

####################################################
###  check participans: small database frontend  ###
####################################################

confirm_payment = config.mail.confirm_payment

############################
###  confirmation email  ###
############################

def send_confirm_payment_mail(participant):
    para = create_parameter_dict(participant=participant)
    para['recipient'] = para['participant'] # add synonym
    Email.sendmail(
        subject = '%s %s: Payment Confirmed' %(config.conference.conference_acronym, config.conference.year),
        message = Email.render_mail('confirm_payment.html', **para),
        fromaddr = config.mail.registration_email,
        to_list = (para['participant'].email,),
        mailformat='html',
        ParticipantID = para['participant'].ID,
    )

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

@blueprint.route('/', methods=['GET', 'POST'])
@blueprint.route('/<action>', methods=['GET', 'POST'])
def show(action=''):

    # check if logged in
    if not 'intern' in session:
        return redirect(url_for('manage_participants.login'))

    # build rank choices for SelectField
    rank_choices = [(rank, rank) for rank in get_ranks()]

    ##########################
    ###  form definitions  ###
    ##########################

    class Participant(BaseForm):

        ID = StringField('ID')
        fullname = StringField('Name')
        institute = StringField('Institute')
        contribution = StringField('Contribution')
        registered = StringField('Registered')
        payment_confirmed = StringField('Payment Confirmed')
        fee = StringField('Fee')
        paid = BooleanField('paid')
        rank = SelectField('rank', choices=rank_choices)
        events = StringField('Event')
        invoice_number = IntegerField('Invoice No.', [validators.Optional()])

    class Participants(BaseForm):

        btest = StringField('', [validators.AnyOf('')])    # Bot Protection

        filter_paid = SelectField('filter paid:', choices=[('all','all'),('yes','yes'), ('no', 'no')], default='all')
        filter_rank = SelectField('filter rank:', choices=[('all', 'all'),], default='all')

        filter_text = StringField('Search for')
        filter_field = SelectField('in Field', choices=[('all', 'all'), ('ID', 'ID'), ('name', 'Firstname/Lastname'), ('firstname', 'Firstname'), ('lastname', 'Lastname'), ('institute', 'Institute'), ('events', 'Events'), ('contribution', 'Contribution')], default='all')

        sort_by = SelectField('sort by', choices=[('ID', 'ID'), ('firstname', 'Firstname'), ('lastname', 'Lastname'), ('institute', 'Institute'), ('events', 'Events'), ('contribution', 'Contribution'), ('invoice_number', 'Invoice No.'), ('time_registered', 'Registered')], default='time_registered')
        sort_reverse =  BooleanField('reverse order', default='checked')

        participants = FieldList(FormField(Participant))

    ### continue with view function

    form = Participants()
    form.filter_rank.choices += rank_choices
    para = create_parameter_dict()

    # update on submit
    if action == 'save':
        if form.validate_on_submit():

            # create database session
            db_session = database.create_session()
            # get data
            while form.participants:

                form_participant = form.participants.pop_entry()
                ID = form_participant.ID.data

                db_participant = db_session.query(database.Participant).get(ID)

                if not db_participant:
                    app.logger.warning('manage participants: ID not found: ' + ID)
                    continue

                db_participant.paid = form_participant.paid.data
                db_participant.rank = form_participant.rank.data
                db_participant.contribution = form_participant.contribution.data.strip()
                db_participant.events = form_participant.events.data.strip().replace(' ','')

                if db_participant.paid and not db_participant.invoice_number:
                    invoice_no = db_session.query(database.Participant)\
                        .order_by(database.Participant.invoice_number.desc()).first().invoice_number
                    if not invoice_no: invoice_no = 0
                    db_participant.invoice_number = invoice_no + 1

                if db_participant.paid and not db_participant.payment_confirmed:
                    db_participant.payment_confirmed = time.time()

                    if confirm_payment:
                        send_confirm_payment_mail(db_participant)

                # save changes to database
                try:
                    db_session.commit()
                except:
                    db_session.rollback()
                    raise
                finally:
                    db_session.close()

    # create database session
    db_session = database.create_session()

    # empty form list
    while form.participants:
        form.participants.pop_entry()

    # prepare new list of participants
    participants = db_session.query(database.Participant).filter(~database.Participant.rank.in_(config.registration.ranks_hidden))

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

    # populate form
    for participant in participants:
        participant_form = Participant()
        participant_form.ID = participant.ID
        participant_form.fullname = participant.fullnamel
        participant_form.institute = participant.institute
        participant_form.contribution = participant.contribution
        participant_form.registered = time.strftime('%d/%m/%Y', time.localtime(participant.time_registered))
        if participant.payment_confirmed:
            participant_form.payment_confirmed = time.strftime('%d/%m/%Y', time.localtime(participant.payment_confirmed))
        else:
            participant_form.payment_confirmed = ''
        participant_form.fee = config.calc_fee(participant)
        participant_form.paid = participant.paid
        #participant_form.rank.choices = rank_choices
        participant_form.rank = participant.rank
        participant_form.events = participant.events
        participant_form.invoice_number = participant.invoice_number
        form.participants.append_entry(participant_form)

    db_session.close()

    # view page
    return render_template('manage_participants.html', form=form, **para)
