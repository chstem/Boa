# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import codecs
from flask import Blueprint, render_template, render_template_string, session, redirect, url_for, current_app, request, jsonify
from flask_wtf.file import FileField, FileAllowed
from glob import glob
import os
import re
from sqlalchemy import or_
from werkzeug import secure_filename

from ...modules import database, config
from ...modules.Email import sendmail
from ...modules.forms import BaseForm, LoginPW, validators, ValidationError
from ...modules.forms import StringField, BooleanField, SelectField, RadioField, TextAreaField, FormField, MultiCheckboxField
from ... import utils
from .. import components_loaded

blueprint = Blueprint('MassMail', __name__, url_prefix='/MassMail', template_folder='templates')

##################
###  settings  ###
##################

attachments_dir = os.path.join(config.instance_path, 'mail_attachments')
templates_dir = os.path.join(config.instance_path, 'mail_templates')
overwrite_drafts = config.components.MassMail.overwrite_drafts
overwrite_files = config.components.MassMail.overwrite_drafts
MAX_FILE_SIZE = config.components.MassMail.MAX_FILE_SIZE
ALLOWED_EXTENSIONS = set(['pdf', 'png', 'jpg', 'jpeg', 'txt', 'doc', 'docx', 'odt'])

####################
###  Form Class  ###
####################

class FMassMail(BaseForm):
    btest = StringField('', [validators.AnyOf('')])    # Bot Protection

    # mail content
    subject = StringField('Subject', [validators.InputRequired()])
    mail_body = TextAreaField('Mail Text', [validators.InputRequired()])

    # attachments
    fileupload = FileField('Upload File', [FileAllowed(list(ALLOWED_EXTENSIONS), 'File type is not valid.')])

    # recipients filter
    conjunction = RadioField('conjunction', choices=[('and','and'),('or','or')], default='and')
    recipients_all = BooleanField('everyone registered in database')
    paid = SelectField('paid', choices=[('disable','disable filter'),('yes','yes'), ('no', 'no')], default='disable')
    abstract_missing = BooleanField('only with missing abstract')
    bcc_filter = StringField('BCC', [validators.Email(), validators.Optional()])

    # recipient list
    recipients_list = StringField('Emails/IDs')
    bcc_list = StringField('BCC', [validators.Email(), validators.Optional()])

    template = BooleanField('Use as template', default=False)
    HTML = BooleanField('HTML Format', default=False)
    filename = StringField('Filename')

##########################
###  helper functions  ###
##########################

def search_attachments():
    """Search for files in <attachments> folder."""

    attachments = []
    for filename in os.listdir(attachments_dir):
        size = os.path.getsize(os.path.join(attachments_dir, filename)) / 1024
        attachments.append((filename, '%s (%.2f KB)' %(filename, size)))

    # sort and return
    return sorted(attachments, key=lambda x:x[1].lower())

def search_drafts():
    """Search for mail templates in <mails> folder."""
    drafts = []

    # search in instance folder
    drafts = [f for f in os.listdir(templates_dir) if os.path.isfile(os.path.join(templates_dir, f))]

    # search in module folder
    for f in os.listdir(os.path.join(config.module_path, 'mail_templates')):
        if f in drafts:
            continue
        if os.path.isfile(os.path.join(config.module_path, 'mail_templates', f)):
            drafts.append(f)

    # sort and return
    return sorted(drafts, key=lambda s:s.lower())

def find_draft(filename):
    """Find full path of draft template file."""

    # search in instance folder
    fullname = os.path.join(templates_dir, filename)
    if os.path.isfile(fullname):
        return fullname

    # search in module folder
    fullname = os.path.join(config.module_path, 'mail_templates', filename)
    if os.path.isfile(fullname):
        return fullname

    # not found
    return ''

def load_draft(filename):
    """Load HTML template."""

    # defaults
    draft = {
        'subject' : '',
        'HTML' : False,
        'template' : False,
        'mail_body' : '',
    }

    if not filename or not os.path.isfile(filename):
        return draft

    # read file
    fd = codecs.open(filename, encoding='utf-8')
    text = fd.readlines()
    fd.close()

    # get data
    for iline, line in enumerate(text):

        if line.startswith('{#SUBJECT:'):
            draft['subject'] = line[10:].strip('#}\n\r ')

        elif line.startswith('{#HTML:'):
            html = line[8:].strip('#}\n\r ')
            if html == 'False':
                draft['HTML'] = False
            else:
                draft['HTML'] = True

        elif line.startswith('{#TEMPLATE:'):
            template = line[11:].strip('#}\n\r ')
            if template == 'False':
                draft['template'] = False
            else:
                draft['template'] = True

        else:
            break

    # mail body
    draft['mail_body'] = ''.join(text[iline:])

    return draft

########################
###  view functions  ###
########################

@blueprint.route('/login/', methods=['GET', 'POST'])
def login():

    # logout previous session
    session.pop('intern', None)

    if not config.internal_password:
        return 'Page is currently offline'

    para = utils.create_parameter_dict(login_failed=False)

    # create form
    form = LoginPW()

    # new login
    if form.validate_on_submit():
        pw = form.password.data
        if pw == config.internal_password:
            session['intern'] = True
            return redirect(url_for('MassMail.MassMail'))
        else:
            form.password.errors.append('Invalid password.')
            return render_template('MassMail_login.html', form=form, **para)

    # view login page
    return render_template('MassMail_login.html', form=form, **para)

@blueprint.route('/', methods=['GET', 'POST'])
@blueprint.route('/<action>', methods=['GET', 'POST'])
def MassMail(action='', draft_filename='', form=None):

    # check if logged in
    if not 'intern' in session:
        return redirect(url_for('MassMail.login'))

    # check if activities extension is loaded
    if 'activities' in components_loaded:
        from ..activities import activities, DBActivities
    else:
        activities = {}

    # create directories
    if not os.path.isdir(attachments_dir):
        os.mkdir(attachments_dir)
    if not os.path.isdir(templates_dir):
        os.mkdir(templates_dir)

    db_session = database.create_session()

    # get contributions/ranks/events
    contributions = utils.get_contributions()
    ranks = utils.get_ranks()
    events = utils.get_events()

    # search for files
    attachments = search_attachments()
    drafts = search_drafts()

    ### create form
    formclass = FMassMail

    # add ranks filter
    formclass = formclass.append_field('ranks_enable', BooleanField('enable filter'))
    for rank in ranks:
        formclass = formclass.append_field('ranks_'+rank, BooleanField(rank))

    # add events filter
    if events:
        formclass = formclass.append_field('events_enable', BooleanField('enable filter'))
    for event in events:
        formclass = formclass.append_field('events_'+event, BooleanField(event))

    # add contributions filter
    formclass = formclass.append_field('contributions_enable', BooleanField('enable filter'))
    for con in contributions:
        formclass = formclass.append_field('contributions_'+con, BooleanField(con))

    # add activities to form
    for group in activities:
        formclass = formclass.append_field('act_'+group['key'], BooleanField('filter %s activities' %group['label']))
        for event in group['events']:
            formclass = formclass.append_field('act_%s_%s' %(group['key'], event['key']), BooleanField(event['label']))

    # add MultiCheckbox
    formclass = formclass.append_field('attachments', MultiCheckboxField('Attach Files', choices=attachments))

    # add SelectField
    formclass = formclass.append_field('drafts', SelectField('Available Drafts', choices=[(fn,fn) for fn in drafts]))

    # load draft and instantiate form
    if draft_filename:

        # I don't know why, but this does not work:
        #form = formclass(**load_draft(draft_filename))

        # so let's do this step-by-step
        draft = load_draft(draft_filename)
        form = formclass()
        form.subject.data = draft['subject']
        form.mail_body.data = draft['mail_body']
        form.HTML.data = draft['HTML']
        form.template.data = draft['template']

        form.filename.data = os.path.basename(draft_filename)

    elif form:

        # reload after file/draft upload: keep form.data
        form = formclass(**form.data)

    else:

        form = formclass()

    # template parameters
    para = utils.create_parameter_dict(
        sent=None,
        ranks = ranks,
        events = events,
        contributions = contributions,
        activities = activities,
        ALLOWED_EXTENSIONS = ', '.join(ALLOWED_EXTENSIONS),
        MAX_FILE_SIZE = MAX_FILE_SIZE / 1024**2,
    )

    ## perform button actions
    if action.startswith('send'):

        # send Mass Mails
        if form.validate_on_submit():

            # get options
            if form.data['HTML']:
                mailformat = 'html'
            else:
                mailformat = 'plain'

            if not form.data['template']:
                message = form.mail_body.data

            # attachments
            attachments = [ os.path.join(attachments_dir, filename) for filename in form.attachments.data ]

            # get all participants (where email is available)
            recipients_all = db_session.query(database.Participant).filter(database.Participant.email != '').filter(~database.Participant.rank.in_(config.registration.ranks_hidden))

            if action == 'send_filter':

                bcc = filter(None, re.split('[,; ]+', form.bcc_filter.data))

                if form.data['recipients_all']:

                    recipients = recipients_all.all()

                else:

                    # get list of requested contributions, ranks and events
                    ranks_list = [ rank for rank in ranks if form.data['ranks_'+rank] ]
                    events_list = [ event for event in events if form.data['events_'+event] ]
                    contributions_list = [ c for c in contributions if form.data['contributions_'+c] ]

                    if form.data['conjunction'] == 'or':

                        recipients = []

                        for key, data in form.data.items():

                            # ranks
                            if key == 'ranks_enable' and form.data[key]:
                                recipients += recipients_all.filter(database.Participant.rank.in_(ranks_list)).all()

                            # events
                            elif key == 'events_enable' and form.data[key]:
                                recipients += recipients_all.filter(or_(*[ database.Participant.events.contains(event) for event in events_list ])).all()

                            # contributions
                            elif key == 'contributions_enable' and form.data[key]:
                                recipients += recipients_all.filter(database.Participant.contribution.in_(contributions_list)).all()

                            # activities
                            elif key.startswith('act_'):
                                splitkey = key.split('_')
                                if len(splitkey) == 2:
                                    if form.data[key]:
                                        groupkey = splitkey[1]
                                        group = utils.get_dict_from_list(activities, 'key', groupkey)

                                        act_list = []
                                        for event in group['events']:
                                            ekey = 'act_%s_%s' %(groupkey, event['key'])
                                            if form.data[ekey]:
                                                act_list.append(event['key'])

                                        recipients += recipients_all.join(DBActivities).filter(\
                                            or_(*[ DBActivities.activities.contains(ekey) for ekey in act_list ])\
                                            ).all()
                                elif len(splitkey) == 3:
                                    continue
                                else:
                                    raise ValueError('invalid key for activities')

                        # paid
                        if form.data['paid'] == 'yes':
                            recipients += recipients_all.filter(database.Participant.paid == True).all()
                        elif form.data['paid'] == 'no':
                            recipients += recipients_all.filter(database.Participant.paid == False).all()

                    elif form.data['conjunction'] == 'and':

                        recipients = recipients_all

                        for key, data in form.data.items():

                            # ranks
                            if key == 'ranks_enable' and form.data[key]:
                                recipients = recipients.filter(database.Participant.rank.in_(ranks_list))

                            # events
                            elif key == 'events_enable' and form.data[key]:
                                recipients = recipients.filter(or_(*[ database.Participant.events.contains(event) for event in events_list ]))

                            # contributions
                            elif key == 'contributions_enable' and form.data[key]:
                                recipients = recipients.filter(database.Participant.contribution.in_(contributions_list))

                            elif key.startswith('act_'):
                                splitkey = key.split('_')
                                if len(splitkey) == 2 :
                                    if form.data[key]:
                                        groupkey = splitkey[1]
                                        group = utils.get_dict_from_list(activities, 'key', groupkey)

                                        act_list = []
                                        for event in group['events']:
                                            ekey = 'act_%s_%s' %(groupkey, event['key'])
                                            if form.data[ekey]:
                                                act_list.append(event['key'])

                                        recipients = recipients.join(DBActivities).filter(\
                                            or_(*[ DBActivities.activities.contains(ekey) for ekey in act_list ])\
                                            )

                                elif len(splitkey) == 3:
                                    continue
                                else:
                                    print(splitkey)
                                    raise ValueError('invalid key for activities')

                        # paid
                        if form.data['paid'] == 'yes':
                            recipients = recipients.filter(database.Participant.paid == True)
                        elif form.data['paid'] == 'no':
                            recipients = recipients.filter(database.Participant.paid == False)

                        recipients = recipients.all()

                # filter for only missing abstracts
                if form.data['contributions_enable'] and form.data['abstract_missing']:
                    recipients = [ r for r in recipients if not r.abstract_submitted ]

                # remove duplicates
                recipients = set(recipients)


            elif action == 'send_list':

                bcc = filter(None, re.split('[,; ]+', form.bcc_list.data))

                # delimiter may be: comma, semicolon, space
                # filter() removes empty strings possibly created by leading and trailing separators
                items = filter(None, re.split('[,; ]+', form.recipients_list.data))

                recipients = []

                # search in database
                for item in items:

                    # check if ID
                    result = db_session.query(database.Participant).get(item)
                    if result:
                        recipients.append(result)
                        continue

                    # check if email
                    results = db_session.query(database.Participant).filter(database.Participant.email == item).all()
                    if not results:
                        # not found, continue with email
                        recipients.append(item)
                    else:
                        # continue with all found results
                        recipients.extend(results)

            # send emails
            for recipient in recipients:

                if isinstance(recipient, database.Participant):

                    # Participant in database: use render_template
                    if form.data['template']:
                        para['participant'] = recipient
                        para['recipient'] = recipient
                        message = render_template_string(form.mail_body.data, **para)
                    else:
                        message = form.mail_body.data

                    #print recipient
                    sendmail(
                        subject = form.subject.data,
                        message = message,
                        fromaddr = config.mail.registration_email,
                        to_list = (recipient.email,),
                        bcc_list = bcc,
                        mailformat=mailformat,
                        attachments = attachments,
                        ParticipantID = recipient.ID,
                    )

                else:

                    # no Participant, send email without rendering
                    if not '@' in item:
                        continue

                    message = form.mail_body.data
                    sendmail(
                        subject = form.subject.data,
                        message = message,
                        fromaddr = config.mail.registration_email,
                        to_list = (item,),
                        bcc_list = bcc,
                        mailformat=mailformat,
                        attachments = attachments,
                        )

            para['sent'] = len(recipients)

    elif action == 'store_draft':

        # filename
        filename = secure_filename(form.filename.data)
        if not filename.endswith('.html'):
            filename += '.html'

        # check if empty
        if not filename:
            form.errors['filename'] = ['Filename already exists.']
            form.filename.errors = ['Filename already exists.']
            db_session.close()
            return render_template('MassMail.html', form=form, **para)

        # check if filename exists
        if not overwrite_drafts and filename in drafts:
            form.errors['filename'] = ['Filename already exists.']
            form.filename.errors = ['Filename already exists.']
            db_session.close()
            return render_template('MassMail.html', form=form, **para)

        # prepend SUBJECT and Options
        text = '{#SUBJECT: %s#}\n' %form.subject.data
        text += '{#HTML: %s#}\n' %form.data['HTML']
        text += '{#TEMPLATE: %s#}\n' %form.data['template']
        text += form.mail_body.data

        # write to file
        fd = codecs.open(os.path.join(templates_dir, filename), 'w', encoding='utf-8')
        fd.write(text)
        fd.close()

        # reload to reinitiate form
        return MassMail(form=form)

    elif action == 'load_draft':

        # get full filename with path
        filename = find_draft(form.drafts.data)

        if not filename:
            # file not found
            form.mail_body.data = ''
            form.errors['drafts'] = [u'Invalid filename.',]
            form.drafts.errors = [u'Invalid filename.',]
        else:
            # reload to reinitiate form
            return MassMail(draft_filename=filename)

    elif action == 'upload':

        # get filename
        fup = request.files['fileupload']
        filename = secure_filename(fup.filename.replace(' ','_'))

        # validate filename
        if not overwrite_files and os.path.isfile(os.path.join(attachments_dir, filename)):
            form.errors['fileupload'] = ['Filename already exists.']
            form.fileupload.errors = ['Filename already exists.']
        else:
            # upload attachment
            if fup:
                fup.save(os.path.join(attachments_dir, filename))
            # reload page to update list of attachment files
            return MassMail(form=form)

    # view page
    db_session.close()
    return render_template('MassMail.html', form=form, **para)
