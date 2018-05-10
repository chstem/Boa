# -*- coding: utf-8 -*-

################################################
###  import modules and init the app object  ###
################################################

from __future__ import unicode_literals, print_function, absolute_import

# general modules
from codecs import open
import hashlib
from multiprocessing import Process
import os
import time
from subprocess import Popen, PIPE, call
import sys

# Flask
from flask import Flask, session, request
from flask import redirect, url_for, send_from_directory
from flask import render_template
from flask import jsonify, flash, abort
from flask_wtf.csrf import CSRFProtect, CSRFError

# submodules
from .modules import config, database, export, forms, pandoc, TexCleaner
from .modules.cache import cache
from .modules.Email import sendmail
from . import utils

### create flask app and enable flask extensions
app = Flask(__name__, static_folder=None)
csrf = CSRFProtect(app)
cache.init_app(app)

# set some parameters
app.debug = False
app.use_evalex = False
app.secret_key = config.flask.secret_key

app.config['MAX_CONTENT_LENGTH'] = config.flask.MAX_FILE_SIZE
app.config['WTF_CSRF_ENABLED'] = config.flask.CSRF_ENABLED
app.config['WTF_CSRF_SECRET_KEY'] = config.flask.CSRF_SECRET_KEY
app.config['WTF_CSRF_TIME_LIMIT'] = config.flask.CSRF_TIME_LIMIT

app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True

if config.is_instance:
    # prefere instance specific templates
    app.jinja_loader.searchpath.insert(0, os.path.join(config.instance_path, 'templates'))

##############################
###  additional functions  ###
##############################

### add shuffle filter to jinja
from random import shuffle

@app.template_filter('shuffle')
def filter_shuffle(seq):
    try:
        result = list(seq)
        shuffle(result)
        return result
    except:
        return seq

### add markdown parser as filter to jinja
@app.template_filter('markdown')
def filter_markdown(md):
    html = pandoc.markdown2html(md)
    html = html.replace('<p>', '').replace('</p>', '')
    return html

### log user statistics
if config.flask.logIPs:
    @app.before_request
    def before_request():
        # store IP in database
        IP = request.remote_addr
        if IP:
            if config.flask.hashIPs:
                md5 = hashlib.md5()
                md5.update(IP.encode())
                IP = md5.hexdigest()
            today = time.strftime('%Y/%m/%d')
            db_session = database.create_session()
            try:
                if not db_session.query(database.IPStatistics).filter(database.IPStatistics.IP == IP).filter(database.IPStatistics.date == today).all():
                    ip = database.IPStatistics(IP=IP, date=today)
                    db_session.add(ip)
                    db_session.commit()
            except database.NoSuchColumnError:
                pass
            finally:
                db_session.close()

### error handling
@app.errorhandler(413)
def request_entity_too_large(error):
    return 'File Too Large, Maximum File Size is %.1f MB' %(config.flask.MAX_FILE_SIZE/1024.**2), 413

from flask import abort
from werkzeug.wrappers import Response

@app.errorhandler(CSRFError)
def csrf_error(reason):
    para = utils.create_parameter_dict(reason=reason, url=request.url)
    return render_template('csrf_error.html', **para)
    abort(Response(render_template('csrf_error.html', **para), status=400, content_type='text/html'))

###########################
###  import components  ###
###########################

from . import components
components.load(app)

####################
###  route URLs  ###
####################

@app.route('/')
def main():
    #return redirect('http://www.example.com')
    return abort(404)

@app.route('/static/<path:filename>')
@app.route('/<path:filename>')
def static(filename):
    """Route to files in static folders."""
    # check instance's static folder first
    dirname, filename = os.path.split(filename)
    static_dir = os.path.join(config.instance_path, 'static', dirname)
    if os.path.isfile(os.path.join(static_dir, filename)):
        return send_from_directory(static_dir, filename)
    # fallback to module's static folder
    return send_from_directory(os.path.join(config.module_path, 'static', dirname), filename)

@app.route('/help')
def help_page():
    para = utils.create_parameter_dict()
    return render_template('help.html', **para)

##########################
###  abstract figures  ###
##########################

def get_figure_fname(ID):
    if ID == 'example':
        # search in instance preferences
        if config.prefs_instance:
            for fname in os.listdir(config.prefs_instance):
                if fname.startswith('abstract_example_figure') and (fname.rsplit('.', 1)[1].lower() in config.forms.ALLOWED_EXTENSIONS):
                    return config.prefs_instance, fname

        # search in defaults preferences
        for fname in os.listdir(config.prefs_default):
            if fname.startswith('abstract_example_figure') and (fname.rsplit('.', 1)[1].lower() in config.forms.ALLOWED_EXTENSIONS):
                return config.prefs_default, fname

    abstract_dir = os.path.join(config.paths.abstracts, ID)
    if os.path.isdir(abstract_dir):
        for fname in os.listdir(abstract_dir):
            if fname.startswith('figure') and (fname.rsplit('.', 1)[1].lower() in config.forms.ALLOWED_EXTENSIONS):
                return abstract_dir, fname

    raise FileNotFoundError

def convert_web(dirname, fname, fname_web):
    """Convert image to a web-friendly format."""
    fname = os.path.join(dirname, fname)
    fname_web = os.path.join(dirname, fname_web)
    call(['convert', '-resize', '700', '-density', '700', fname, fname_web])

@app.route('/images/<ID>')
@utils.nocache
def images(ID):
    try:
        abstract_dir, fname = get_figure_fname(ID)
    except FileNotFoundError:
        return abort(404)
    return send_from_directory(abstract_dir, fname)

@app.route('/images_web/<ID>')
@utils.nocache
def images_web(ID):
    abstract_dir, fname = get_figure_fname(ID)
    # check for existing web-friendly version
    name, ext = fname.rsplit('.', 1)
    if ext.lower() == 'pdf':
        ext = 'png'
    fname_web = '%s_web.%s' %(name, ext)
    # check timestamp of existing file
    if os.path.isfile(os.path.join(abstract_dir, fname_web)):
        if os.path.getmtime(os.path.join(abstract_dir, fname)) < os.path.getmtime(os.path.join(abstract_dir, fname_web)):
            return send_from_directory(abstract_dir, fname_web)
    # check file format
    if fname.lower().endswith('pdf'):
        convert_web(abstract_dir, fname, fname_web)
        return send_from_directory(abstract_dir, fname_web)
    # check file size
    if os.path.getsize(os.path.join(abstract_dir, fname)) > 1000**2:
        convert_web(abstract_dir, fname, fname_web)
        return send_from_directory(abstract_dir, fname_web)
    # original picture will be just fine
    return send_from_directory(abstract_dir, fname)

@app.route('/portraits/<ID>')
@utils.nocache
def portraits(ID):
    abstract_dir = os.path.join(config.paths.abstracts, ID)
    for fname in os.listdir(abstract_dir):
        if fname.startswith('portrait') and (fname.rsplit('.', 1)[1].lower() in config.forms.ALLOWED_EXTENSIONS):
            return send_from_directory(abstract_dir, fname)

############################################
###  Access and Registration Statistics  ###
############################################

@app.route('/stats/')
def stats():

    para = {}

    # website access
    IPstats = utils.get_IP_statistics()
    IPstats.reverse()
    para['IPstats'] = IPstats[:30]

    # registered participants
    db_session = database.create_session()
    participants = db_session.query(database.Participant)
    participants_nohidden = participants.filter(~database.Participant.rank.in_(config.registration.ranks_hidden))
    para['participants_total'] = participants_nohidden.count()

    # events/ranks/contributions
    events = utils.get_events()
    ranks = utils.get_ranks()
    contributions = utils.get_contributions()

    # events
    para['events'] = {}
    for event in events:
         para['events'][event] = participants_nohidden.filter(database.Participant.events.contains(event)).count()

    # ranks
    para['ranks'] = {}
    for rank in ranks:
        para['ranks'][rank] = participants_nohidden.filter(database.Participant.rank == rank).count()

    # contributions
    para['contributions'] = {}
    para['contributions_submitted'] = {}
    for con in contributions:
        if con.lower() == 'none':
            continue
        abstracts = participants.filter(database.Participant.contribution == con)
        para['contributions'][con] = abstracts.count()
        para['contributions_submitted'][con] = len([p for p in abstracts.all() if p.abstract_submitted])

    db_session.close()

    return render_template('stats.html', **para)

######################
###  Registration  ###
######################

@app.route('/register/', methods=['GET', 'POST'])
@app.route('/register/<rank>', methods=['GET', 'POST'])
def register(rank='participant'):

    onsite = rank == 'onsite'
    if onsite:
        rank = 'participant'

    para = utils.create_parameter_dict(
        rank = rank,
        onsite = onsite,
        events = config.registration.events,
        reject_email = False,
        address = rank in config.registration.ranks,
    )

    if not onsite:

        if not rank in config.registration.ranks + config.registration.ranks_invited:
            return abort(404)
            return redirect(url_for('register'))

        if not rank in config.registration.keep_open and rank != 'onsite':
            regclosed = utils.registration_isclosed()
            if regclosed:
                return render_template('registration_closed.html', reason=regclosed, **para)

    ## create form
    # select form class
    if onsite:
        formclass = forms.RegistrationNoMail
    elif rank in config.registration.ranks_invited:
        formclass = forms.Registration_invited
    else:
        formclass = forms.Registration

    # add event fields
    for event in config.registration.events:
        formclass = formclass.append_field('events_'+event, forms.BooleanField(event))
    form = formclass()

    # add contribution choices
    if not rank in config.registration.ranks_invited:
        form.contribution.choices = utils.get_contribution_choices()

    ## get input data
    if form.validate_on_submit():

        db_session = database.create_session()

        # check if email already registered (to avoid double registration)
        if config.registration.reject_double_registration and form.email.data:
            if db_session.query(database.Participant).filter(database.Participant.email == form.email.data).all():
                para['reject_email'] = True
                db_session.close()
                return render_template('registration_open.html', form=form, **para)

        # get events
        events = ','.join([ event for event in config.registration.events if form.data['events_'+event] ])

        if config.registration.events and not events:
            for event in config.registration.events:
                getattr(form, 'events_'+event).errors.append('No event selected.')
            db_session.close()
            return render_template('registration_open.html', form=form, **para)

        # get title
        if form.title.data == 'other':
            title = form.title_alt.data
        else:
            title = config.titles[int(form.title.data)]

        # get gender
        if config.genders:
            gender = config.genders[int(form.gender.data)]
        else:
            gender = None

        # get institute
        if not config.institute_presets:
            institute = form.institute.data
        elif form.institute.data == 'other':
            institute = form.institute_alt.data
        else:
            institute = dict(form.institute.choices).get(form.institute.data)

        # get contribution
        if not config.submission.events:
            # accept all
            contribution = form.contribution.data
        elif set(events.split(',')) & set(config.submission.events):
            # only if registering for event with submission
            contribution = form.contribution.data
        else:
            contribution = 'None'

        # get new ID
        ID = utils.create_new_ID()

        # save to database
        if rank in config.registration.ranks_invited:
            participant = database.Participant(
                        ID = ID,
                        firstname = form.firstname.data,
                        lastname = form.lastname.data,
                        title = title,
                        gender = gender,
                        email = form.email.data,
                        institute = institute,
                        department = form.department.data,
                        country = config.countries[int(form.country.data)],
                        events = events,
                        paid = False,
                        rank = rank,
                        abstract = None,
                        time_registered = time.time(),
                        )
        else:
            participant = database.Participant(
                        ID = ID,
                        firstname = form.firstname.data,
                        lastname = form.lastname.data,
                        title = title,
                        gender = gender,
                        email = form.email.data,

                        institute = institute,
                        department = form.department.data,

                        address_line1 = form.address_line1.data,
                        address_line2 = form.address_line2.data,
                        street = form.street.data,
                        postal_code = form.postal_code.data,
                        city = form.city.data,
                        country = config.countries[int(form.country.data)],
                        tax_number = form.tax_number.data,

                        time_registered = time.time(),
                        contribution = contribution,
                        events = events,
                        paid = False,
                        rank = rank,
                        abstract = None,
                        )

        try:
            db_session.add(participant)
            db_session.commit()
        except:
            db_session.rollback()
            db_session.close()
            raise

        para['ID'] = participant.ID

        # send confirmation email
        if rank in config.registration.ranks and not onsite:
            para['participant'] = participant
            utils.send_reg_mail(para)

        db_session.close()

        return render_template('registration_success.html', **para)

    # render html page
    return render_template('registration_open.html', form=form, **para)

#############################
###  Abstract Submission  ###
#############################

@app.route('/abstract_submission/login/<restricted>', methods=['GET', 'POST'])
@app.route('/abstract_submission/restricted/', methods=['GET', 'POST'], defaults={'restricted':'restricted'})
@app.route('/abstract_submission/login/', methods=['GET', 'POST'])
def abstract_submission_login(restricted=''):

    if not restricted in ('', 'restricted'):
        abort(404)

    # logout previous session
    session.pop('ID_submission', None)

    para = utils.create_parameter_dict(restricted=restricted)

    # check if regular submission is open
    reason = utils.abstract_submission_isclosed()
    if not restricted and reason and not '_' in reason:
        return render_template('abstract_submission_closed.html', reason=reason, **para)

    # create form
    form = forms.LoginID()

    # new login
    if form.validate_on_submit():

        ID = form.ID.data

        # get participant
        if ID == 'example':
            from abstract_example import participant
        else:
            db_session = database.create_session()
            participant = db_session.query(database.Participant).get(ID)

        if not participant:
            db_session.close()
            form.ID.errors.append('Invalid ID.')
            return render_template('abstract_submission_login.html', form=form, **para)

        # check if allowed
        if not participant.rank in config.submission.keep_open:

            # check event participation
            if ID != 'example' and config.submission.events and not set(participant.events.split(',')) & set(config.submission.events):
                # no abstracts for this event
                db_session.close()
                form.ID.errors.append('Invalid ID.')
                return render_template('abstract_submission_login.html', form=form, **para)

            # check contribution type deadline
            if reason and participant.contribution.lower() in reason:
                return render_template('abstract_submission_closed.html', reason=reason, **para)

            # check restricted access
            if restricted and not participant.ID in config.submission.allow_IDs:
                db_session.close()
                form.ID.errors.append('Invalid ID.')
                return render_template('abstract_submission_login.html', form=form, **para)

        # login succesful
        session['ID_submission'] = ID
        if not ID == 'example':
            db_session.close()
        return redirect(url_for('abstract_submission'))

    # form validation failed
    return render_template('abstract_submission_login.html', form=form, **para)

def abstract_submission_check_login(ID):
    """Check if logging in is allowed for ID."""

    # check if abstract submission open
    reason = utils.abstract_submission_isclosed()
    if reason == 'notyet':
        return False

    db_session = database.create_session()

    # get participant
    if ID == 'example':
        from abstract_example import participant
    else:
        participant = db_session.query(database.Participant).get(ID)

    if not participant:
        return False

    # check rank for keep open
    if participant.rank in config.submission.keep_open:
        db_session.close()
        return True

    # check event participation
    if ID != 'example' and config.submission.events and not set(participant.events.split(',')) & set(config.submission.events):
        # no abstracts for this event
        db_session.close()
        return False

    # check ID for exceptions
    if not participant.ID in config.submission.allow_IDs:
        db_session.close()

    # check contribution type deadline
    if reason == 'deadline' or participant.contribution.lower() in reason:

        # past deadline; check for allowed exceptions
        if not participant.ID in config.submission.allow_IDs:
            # no execption for this ID
            db_session.close()
            return False

    db_session.close()

    # no reasons found; ID is permitted
    return True

@app.route('/abstract_submission/', methods=['GET', 'POST'])
#@app.route('/abstract_submission/<restricted>', methods=['GET', 'POST'])
def abstract_submission():

    #if not restricted in ('', 'restricted'):
        #abort(404)

    # check if logged in
    if not 'ID_submission' in session:
        return redirect(url_for('abstract_submission_login', restricted=''))

    # check if login still allowed
    ID = session['ID_submission']
    if not abstract_submission_check_login(ID):
        session.pop('ID_submission', None)
        return redirect(url_for('abstract_submission_login', restricted=''))

    # get participant
    if ID == 'example':
        from abstract_example import participant
    else:
        db_session = database.create_session()
        participant = db_session.query(database.Participant).get(ID)

    # check if abstract already available
    if not participant.abstract:

        # create new data
        new_abstract = database.Abstract(
            category = None,
            title = '',
            content = '\\placetitle' if participant.rank in config.registration.ranks_invited else '',
            img_use = False,
            img_width = 100,
            img_caption = ''
            )
        new_abstract.authors.append(utils.create_new_author(participant=participant))
        new_abstract.affiliations.append(utils.create_new_affiliation(participant=participant))

        participant.abstract = new_abstract

        # save to database
        try:
            db_session.commit()
        except:
            db_session.rollback()
            db_session.close()
            raise

    # create form
    if request.method == 'GET':
        form = utils.populate_abstract_form(participant)
    elif request.method == 'POST':
        form = utils.create_abstract_form(participant)

    # submit data
    if (request.method == 'POST') and not (ID == 'example'):

        if form.validate():
            # submit changes to database
            success = utils.submit_abstract(participant, form, request)

            # save to database
            if success:
                try:
                    db_session.commit()
                    if 'BoA_online' in components.components_loaded:
                        cache.delete_memoized(components.BoA_online.abstract, ID)
                        if participant.abstract.label:
                            cache.delete_memoized(components.BoA_online.abstract, participant.abstract.label)
                except:
                    db_session.rollback()
                    db_session.close()
                    raise

        else:
            if not 'img_upload' in form.errors.keys():
                utils.upload_abstract_figure(participant, form, request)

                # save to database
                try:
                    db_session.commit()
                except:
                    db_session.rollback()
                    db_session.close()
                    raise

            if participant.rank in config.registration.ranks_invited and not 'portrait_upload' in form.errors.keys():
                utils.upload_portrait(participant, request)

        # update possibly changed data
        form.img_use.data = participant.abstract.img_use

    # view page
    para = utils.create_parameter_dict(
        institute_presets = config.institute_presets,
        institute_names = [ institute[0] for institute in config.institute_presets ],
        countries = config.countries,
        ALLOWED_EXTENSIONS = ', '.join(config.forms.ALLOWED_EXTENSIONS),
        MAX_FILE_SIZE = config.flask.MAX_FILE_SIZE / 1024**2,
        categories = config.categories[participant.rank],
        invited = participant.rank in config.registration.ranks_invited,
        )
    para['ID'] = participant.ID
    para['figure_available'] = utils.figure_available(ID)
    para['portrait_available'] = utils.portrait_available(ID)

    if ID != 'example':
        db_session.close()

    return render_template('abstract_submission_open.html', form=form, **para)

@app.route('/preview/<ID>')
@app.route('/preview/<ID>.pdf')
@utils.nocache
def preview(ID):
    """Preview abstract as PDF."""
    abstract_dir = os.path.join(config.paths.abstracts, ID)
    return send_from_directory(abstract_dir, ID+'.pdf')

@app.route('/create_preview/', methods=['GET', 'POST'])
def create_preview():

    # check if logged in
    if not 'ID_submission' in session:
        return redirect(url_for('abstract_submission_login'))
    ID = session['ID_submission']

    # show pdf directly for ID == 'example'
    if ID == 'example':
        return redirect(url_for('show_preview'))

    # check if login still allowed
    ID = session['ID_submission']
    if not abstract_submission_check_login(ID):
        session.pop('ID_submission', None)
        return redirect(url_for('abstract_submission_login'))

    # get participant
    if ID == 'example':
        from abstract_example import participant
    else:
        db_session = database.create_session()
        participant = db_session.query(database.Participant).get(ID)

    # create form
    if request.method == 'GET':
        form = utils.populate_abstract_form(participant)
    elif request.method == 'POST':
        form = utils.create_abstract_form(participant)

    if form.validate_on_submit():

        # save changes
        success = utils.submit_abstract(participant, form, request)

        if success:

            halt_latex = participant.halt_latex_on_error

            # save to database
            try:
                db_session.commit()
            except:
                db_session.rollback()
                raise
            finally:
                db_session.close()

            # check supplied data (redundant)
            problems = export.check_abstract(ID)

            if problems:
                para = utils.create_parameter_dict(problems=problems)
                return render_template('incomplete_abstract_data.html', form=form, **para)

            # create preview
            p = Process(target=utils.make_preview, args=(ID,), kwargs={'halt_latex':halt_latex})
            p.start()

            return redirect(url_for('preview_progress'))

        else:

            if not 'img_upload' in form.errors.keys():

                utils.upload_abstract_figure(participant, form, request)

                # save to database
                try:
                    db_session.commit()
                except:
                    db_session.rollback()
                    db_session.close()
                    raise

            if participant.rank in config.registration.ranks_invited and not 'portrait_upload' in form.errors.keys():

                utils.upload_portrait(participant, request)

    # check if img_use updated
    form.img_use.data = participant.abstract.img_use

    # error in form: return to submission
    para = utils.create_parameter_dict(
        institute_presets = config.institute_presets,
        institute_names = [ institute[0] for institute in config.institute_presets ],
        countries = config.countries,
        ALLOWED_EXTENSIONS = ', '.join(config.forms.ALLOWED_EXTENSIONS),
        MAX_FILE_SIZE = config.flask.MAX_FILE_SIZE / 1024**2,
        invited = participant.rank in config.registration.ranks_invited,
        )
    para['ID'] = participant.ID
    para['figure_available'] = figure_available(ID)
    para['portrait_available'] = portrait_available(ID)

    if ID != 'example':
        db_session.close()

    return render_template('abstract_submission_open.html', form=form, **para)

@app.route('/preview_progress/')
def preview_progress():
    para = utils.create_parameter_dict()
    return render_template('preview_progress.html', **para)

@app.route('/_preview_progress/')
def _preview_progress():
    """Check progress with AJAX."""

    # check if logged in
    if not 'ID_submission' in session:
        return jsonify(latex='done')

    ID = session['ID_submission']

    if os.path.isfile(os.path.join(config.paths.abstracts,ID,ID+'.log')):
        return jsonify(latex='done')

    return jsonify(latex='running')

@app.route('/show_preview/')
def show_preview():

    # check if logged in
    if not 'ID_submission' in session:
        return redirect(url_for('abstract_submission_login'))
    ID = session['ID_submission']

    # check if login still allowed
    ID = session['ID_submission']
    if not abstract_submission_check_login(ID):
        session.pop('ID_submission', None)
        return redirect(url_for('abstract_submission_login'))

    para = utils.create_parameter_dict(ID=ID)

    if ID == 'example':

        para['Npages'] = 1
        para['halt_latex'] = 0
        para['delims'] = 0

    else:

        # get number of pages
        cmd = [
            'bash',
            os.path.join(config.paths.BoA, 'count_pdf_pages.sh'),
            os.path.join(config.paths.abstracts, ID, ID+'.pdf')
            ]
        p = Popen(cmd, stdout=PIPE)
        output = p.communicate()
        para['Npages'] = int(output[0].strip())

        db_session = database.create_session()

        # read log file
        participant = db_session.query(database.Participant).get(ID)
        halt_latex = participant.halt_latex_on_error

        # check for unbalanced delimiters
        para['delims'] = TexCleaner.check_balanced_delimiters(participant.abstract.content)

        db_session.close()

        try:
            para['tex_log'] = export.check_log(ID)
        except UnicodeDecodeError:
            app.logger.warning('Error reading logfile for ID %s\n%s' %(ID, sys.exc_info()[0]))
            para['tex_log'] = 'Error reading logfile'

        para['halt_latex'] = halt_latex

    # show preview
    return render_template('show_preview.html', **para)

if app.config.get('ENV', '') == 'production':
    # run server in production mode
    import logging
    from .modules import ErrorLog

    app.logger.addHandler(ErrorLog.file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('app started, Python version %s' %sys.version.replace('\n', ''))

    if config.mail.error_email:
        app.logger.addHandler(ErrorLog.get_mail_handler(app))
