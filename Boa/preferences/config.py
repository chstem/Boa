## NOTE:
# Changes require a restart of the application to be effective.
# about time format see: https://docs.python.org/2/library/time.html#time.strftime

##########################
###  general settings  ###
##########################

internal_password = 'adminonly'    # to restrict access to internal feature with access to the database

##############################################
###  Registration and Abstract Submission  ###
##############################################

registration.enabled = True
registration.start = strptime('01/01/2000 00:00', '%d/%m/%Y %H:%M')        # empty string to disable
registration.deadline = strptime('01/01/2099 13:59', '%d/%m/%Y %H:%M')     # empty string to disable
registration.earlybird = strptime('01/01/2099 23:59', '%d/%m/%Y %H:%M')    # empty string to disable
registration.surcharge = strptime('01/01/2099 23:59', '%d/%m/%Y %H:%M')    # empty string to disable
registration.max_participants = 0               # 0 for infinite
registration.reject_double_registration = True  # checks if email already in database
registration.ranks = ['staff', 'participant']   # address required
registration.ranks_invited = ['invited',]       # no address fields
registration.ranks_hidden = ['second_contribution',]
registration.keep_open = ['staff', 'invited']   # keep registration always open for these ranks
registration.events = []                        # list of main events where independent registration is possible; empty for only one option

submission.enabled = True
submission.start = strptime('01/01/2000 00:00', '%d/%m/%Y %H:%M')               # empty string to disable
submission.deadline_poster = strptime('01/01/2099 23:59', '%d/%m/%Y %H:%M')     # empty string to disable
submission.deadline_talks = strptime('01/01/2099 23:59', '%d/%m/%Y %H:%M')      # empty to use same deadline as for poster
submission.abstract_length = 5000           # maximum number of characters allowed for abstract
submission.require_figure_caption = True    # require a caption if a figure is used in astract
submission.N_backup_abstracts = 5           # number of latest versions to keep for each abstract
submission.keep_open = ['invited']          # keep submission always open for these ranks
submission.allow_IDs = ['example', ]        # allow access even after deadline (because there is always somebody asking for exceptions)
submission.events = []                      # events with abstract submission

##################################################
###  conference data (used in HTML templates)  ###
##################################################

## set your desired time (date) format (https://docs.python.org/2/library/time.html#time.strftime)
timeformat = '%A, %B %d %Y'
timeformat = '%a, %d %b %Y'

conference.year = '2018'
conference.conference_name = 'CONFERENCE NAME'
conference.conference_acronym = 'CONFERENCE ACRONYM'
conference.place = 'CITY'
conference.country = 'Germany'
conference.date = '1th April 2099'
conference.support_email = 'support@example.com'    # support email to make public on webpage

# bank account
conference.account.holder = 'Account Holder'
conference.account.reference = '%s %s [ID]' %(conference.conference_acronym, conference.year)
conference.account.bank = 'Bank'
conference.account.SWIFT = 'SWIFT'
conference.account.IBAN = 'IBAN'

# convert deadlines to strings
conference.start_registration = strftime(timeformat, registration.start)
conference.deadline_registration = strftime(timeformat, registration.deadline)
conference.deadline_payment = '01 April 2099'
conference.deadline_earlybird = strftime('%d %b %Y', registration.earlybird)
conference.start_submission = strftime(timeformat, submission.start)
if submission.deadline_poster:
    conference.deadline_poster = strftime(timeformat, submission.deadline_poster)
else:
    conference.deadline_poster = ''
if submission.deadline_talks:
    conference.deadline_talks = strftime(timeformat, submission.deadline_talks)
else:
    conference.deadline_talks = ''

########################
###  conference fee  ###
########################

def calc_fee(participant):
    """Calculate fee to allow more complex cases."""
    return '10.00'

#############################
###  email configuration  ###
#############################

mail.enable = False                                     # maybe disable this for testing
mail.confirm_payment = True                             # send mail to participant, when marked as paid
mail.error_email = 'admin@example.com'                  # on error, send an email to this address
mail.registration_email = 'registration@example.com'    # will appear as 'sender' in mails
mail.SENDMAIL = '/usr/sbin/sendmail'                    # sendmail location, try:  '/usr/lib/sendmail' or '/usr/sbin/sendmail' or use 'SMTP'
mail.enable_history = True                              # store sent emails in database

# only required when using SMTP:
mail.SMTPServer = 'smtp.example.com'
mail.SMTPPort = 587
mail.SMTPUsername = 'user'
mail.SMTPPassword = r'password'
mail.SMTPSecure = 'STARTTLS'                            # 'STARTTLS', 'SSL', or ''

################################################
###  web framework (flask) related settings  ###
################################################

flask.MAX_FILE_SIZE = 5 * 1024**2   # max file size for uploaded figures (in Bytes)
flask.test_port = 80                # only for test deployment
flask.CSRF_ENABLED = True           # True is highly recommended
flask.CSRF_TIME_LIMIT = 3600*6      # seconds until CSRF token becomes invalid
flask.logIPs = False                # log user IPs for statistics
flask.hashIPs = True                # anonymize IPs by hashing them

# good secret keys may be generated with os.urandom(24)
flask.secret_key = 'changeme'
flask.CSRF_SECRET_KEY = 'changemeto'

#########################################
### form and upload related settings  ###
#########################################

forms.default_country = conference.country
forms.ALLOWED_EXTENSIONS = set(['pdf', 'png', 'jpg', 'jpeg'])    # for figure upload

########################
###  Participant ID  ###
########################

ID.alphabet = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIKLMNPQRSTUVWXYZ123456789'    # list of possible characters for the ID
ID.length = 8    # if changed, make sure to update structure in database, otherwise values might get cut off

##################
###  database  ###
##################

# simplified MySQL setup
database.driver = 'mysql'
database.name = ''
database.user = ''
database.password = r''
database.host = 'localhost'

# generic driver setup, see: http://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls
database.driver = 'sqlite:///test.db'

###############
###  paths  ###
###############

paths.BoA = 'BoA'               # relative to instance directory or absolute
paths.abstracts = 'abstracts'   # relative to paths.BoA or absolute
paths.backup = 'backup'         # backup deleted participants; relative to instance directory or absolute

####################
###  components  ###
####################

components.enable = 'main'       # 'main', all, '' or list of strings

components.sponsors.sponsors = [
    # (NAME, WEBSITE, LOGO FILENAME (stored in static dir))
    ('company name', 'https://www.example.com', 'logo.png'),
]
components.sponsors.organizers = []

components.CV_upload.folder = 'CV_uploads'
components.CV_upload.allowed_files = ['pdf',]
components.CV_upload.deadline = strptime('01/01/2099 23:59', '%d/%m/%Y %H:%M')    # empty to disable
components.CV_upload.restrict_events = []

components.feedback.surveys = ['example']   # place <survey>.json in preferences/feedback directory
components.feedback.plot_figures = True     # plot graphs for results (requires matplotlib)

components.MassMail.overwrite_drafts = True     # overwrite mail drafts
components.MassMail.overwrite_files = True      # overwrite files uploaded as attachment
components.MassMail.ALLOWED_EXTENSIONS = set(['pdf', 'png', 'jpg', 'jpeg', 'txt', 'doc', 'docx', 'odt'])
components.MassMail.MAX_FILE_SIZE = flask.MAX_FILE_SIZE  # for attachments
