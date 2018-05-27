# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import os
from time import localtime
from subprocess import Popen
from werkzeug import secure_filename

from ..modules import config, database, export
from ..modules import MDCleaner as mc
from .contributions import accept_poster, accept_talks

def abstract_submission_isclosed():

    # check config setting
    if not config.submission.enabled:
        return 'closed'

    # check start
    if config.submission.start and config.submission.start > localtime():
        return 'notyet'

    # check deadlines
    poster = accept_poster()
    talks = accept_talks()

    if not talks and not poster:
        return 'deadline'
    if not talks:
        return 'deadline_talks'
    if not poster:
        return 'deadline_poster'

    return ''

def create_new_author(key=0, participant=None):
    if participant:
        author = database.Author(
            key = 1,
            firstname = participant.firstname,
            lastname = participant.lastname,
            affiliation_keys = '1'
            )
    else:
        author = database.Author(
            key = key,
            firstname = '',
            lastname = '',
            affiliation_keys = ''
            )
    return author

def create_new_affiliation(key=0, participant=None):
    if participant:
        affiliation = database.Affiliation(
            key=1,
            institute = participant.institute,
            department = participant.department,
            street = '',
            postal_code = '',
            city = '',
            country = config.forms.default_country,
            )
        if participant.institute == participant.address_line1:
            affiliation.street = participant.street
            affiliation.postal_code = participant.postal_code
            affiliation.city = participant.city
            affiliation.country = participant.country
    else:
        affiliation = database.Affiliation(
            key=key,
            institute = '',
            department = '',
            street = '',
            postal_code = '',
            city = '',
            country = config.forms.default_country,
            )
    return affiliation

def submit_abstract(participant, form, request):
    """Read form data and update database object."""

    ## check number of affiliations and authors
    if not (1 <= len(form.affiliations.entries) < 10):
        return 0    # error
    if not 1 <= len(form.authors.entries) < 10:
        return 0    # error

    if len(form.affiliations.entries) < len(participant.abstract.affiliations):

        # delete affilations
        for i in range(len(participant.abstract.affiliations) - len(form.affiliations.entries)):
            participant.abstract.affiliations.remove(participant.abstract.affiliations[-1])

    elif len(form.affiliations.entries) > len(participant.abstract.affiliations):

        # create new affiliations
        for i in range(len(form.affiliations.entries) - len(participant.abstract.affiliations)):
            new_affiliation = create_new_affiliation(key=participant.abstract.get_new_affiliation_key())
            participant.abstract.affiliations.append(new_affiliation)

    if len(form.authors.entries) < len(participant.abstract.authors):

        # delete authors
        for i in range(len(participant.abstract.authors) - len(form.authors.entries)):
            participant.abstract.authors.remove(participant.abstract.authors[-1])

    elif len(form.authors.entries) > len(participant.abstract.authors):

        # create new authors
        for i in range(len(form.authors.entries) - len(participant.abstract.authors)):
            new_author = create_new_author(key=participant.abstract.get_new_author_key())
            participant.abstract.authors.append(new_author)

    ## update affiliations
    for affil in participant.abstract.affiliations:

        affil_form = form.affiliations.entries[affil.key-1]

        if not config.institute_presets:
            affil.institute = affil_form.institute.data
        elif affil_form.institute.data == 'other':
            affil.institute = affil_form.institute_alt.data
        else:
            affil.institute = dict(config.forms.institute_choices).get(affil_form.institute.data)

        affil.department = affil_form.department.data
        affil.street = affil_form.street.data
        affil.postal_code = affil_form.postal_code.data
        affil.city = affil_form.city.data
        affil.country = config.forms.country_choices[int(affil_form.country.data)][1]

    ## update authors
    for author in participant.abstract.authors:

        author_form = form.authors.entries[author.key-1]

        author.firstname = author_form.firstname.data
        author.lastname = author_form.lastname.data

        # get list of affiliations
        affils = ''
        for char in author_form.affiliations.data:
            if not char.isdigit():
                continue
            if int(char) > len(participant.abstract.affiliations):
                continue
            if not char in affils:
                affils += char

        # have at least one affiliation
        if not affils:
            affils = '1'

        # store in database object
        author.affiliation_keys = affils

        # update form field
        author_form.affiliations.data = ', '.join(affils)

    ## update participant parameters
    if participant.rank in config.registration.ranks:
        if participant.contribution != form.data['contribution']:
            if accept_talks() or (form.data['contribution'] != 'Talk'):
                participant.contribution = form.data['contribution']

    participant.halt_latex_on_error = form.data['halt_on_error']

    ## update abstract
    participant.abstract.category = dict(form.category.choices).get(form.category.data)
    if participant.abstract.category == '(please choose)':
        participant.abstract.category = None
    participant.abstract.title = form.data['title']
    participant.abstract.content = form.data['content']

    participant.abstract.img_caption = form.data['img_caption'].replace('\r', '')
    participant.abstract.img_width = form.data['img_width']

    # fix possible markdown issues
    participant = fix_markdown(participant)

    ## upload figure
    upload_abstract_figure(participant, form, request)
    if participant.rank in config.registration.ranks_invited:
        upload_portrait(participant, request)

    return 1    # success

def fix_markdown(participant):
    """Correct Markdown input."""

    # check if all brackets closed
    delims = mc.check_balanced_delimiters(participant.abstract.content, delims='{[')

    if delims:
        return participant

    # correct missing math mode
    participant.abstract.title = mc.ensure_mathmode(participant.abstract.title)
    participant.abstract.content = mc.ensure_mathmode(participant.abstract.content)
    participant.abstract.img_caption = mc.ensure_mathmode(participant.abstract.img_caption)

    # remove figures
    participant.abstract.title = mc.filter_figures(participant.abstract.title)
    participant.abstract.content = mc.filter_figures(participant.abstract.content)
    participant.abstract.img_caption = mc.filter_figures(participant.abstract.img_caption)

    return participant

def make_preview(ID, halt_latex=True):
    export.abstract.cycle_files(ID)
    export.abstract.write_tex(ID)
    cmd = ['bash', os.path.join(config.paths.BoA,'make_preview.sh'), '-d', ID]
    if halt_latex:
        cmd.append('-h')
    Popen(cmd)

#################
###  figures  ###
#################

def figure_available(ID):
    if ID == 'example':
        for filename in os.listdir('static'):
            if filename.startswith('abstract_example_figure'):
                return filename.rsplit('.', 1)[1].lower()

    path = os.path.join(config.paths.abstracts,ID)
    if os.path.isdir(path):
        for filename in os.listdir(path):
            if filename.startswith('figure'):
                return filename.rsplit('.', 1)[1].lower()

    return False

def delete_figure(ID):
    path = os.path.join(config.paths.abstracts,ID)
    for filename in os.listdir(path):
        if filename.startswith('figure'):
            os.remove(os.path.join(path, filename))

def portrait_available(ID):
    path = os.path.join(config.paths.abstracts,ID)
    if os.path.isdir(path):
        for filename in os.listdir(path):
            if filename.startswith('portrait'):
                return filename.rsplit('.', 1)[1].lower()

    return False

def delete_portrait(ID):
    path = os.path.join(config.paths.abstracts,ID)
    for filename in os.listdir(path):
        if filename.startswith('portrait'):
            os.remove(os.path.join(path, filename))


def upload_abstract_figure(participant, form, request):

    ## delete figure
    if form.data['img_delete']:
        delete_figure(participant.ID)

    ## figure upload
    new_img = False
    fup = request.files.get('img_upload', None)
    if fup:
        abstract_dir = os.path.join(config.paths.abstracts,participant.ID)
        if not os.path.isdir(abstract_dir):
            os.mkdir(abstract_dir)
        filename = secure_filename(fup.filename)
        file_extension = filename.rsplit('.', 1)[1].lower()
        if file_extension in config.forms.ALLOWED_EXTENSIONS:
            # delete previous figure
            delete_figure(participant.ID)
            # save figure
            fup.save(os.path.join(abstract_dir, 'figure.'+file_extension))
            # set flag
            new_img = True

    ## include figure?
    if (new_img or form.data['img_use']) and figure_available(participant.ID):
        participant.abstract.img_use = True
    else:
        participant.abstract.img_use = False

def upload_portrait(participant, request):

    fup = request.files.get('portrait_upload', None)
    if fup:
        abstract_dir = os.path.join(config.paths.abstracts,participant.ID)
        if not os.path.isdir(abstract_dir):
            os.mkdir(abstract_dir)
        filename = secure_filename(fup.filename)
        file_extension = filename.rsplit('.', 1)[1].lower()
        if file_extension in config.forms.ALLOWED_EXTENSIONS:
            # delete previous figure
            delete_portrait(participant.ID)
            # save figure
            fup.save(os.path.join(abstract_dir, 'portrait.'+file_extension))
