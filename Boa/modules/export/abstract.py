# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from builtins import str
import codecs
from glob import glob
import os
from shutil import copy

from .. import config
from ..database import *
from .. import pandoc

####################################################################
###  double check if all required database fields are available  ###
####################################################################

def check_abstract(ID):

    db_session = create_session()
    participant = db_session.query(Participant).get(ID)

    # perfrom checks on provided data
    problems = []

    # check authors
    for author in participant.abstract.get_authors():
        if participant.rank in config.registration.ranks and not author.affiliation_keys:
            problems.append('Please provide at least one affiliation for Author %i.' %author.key)
        if not author.firstname:
            problems.append('Please provide a first name for Author %i.' %author.key)
        if not author.lastname:
            problems.append('Please provide a last name for Author %i.' %author.key)

    # check affiliations
    if participant.rank in config.registration.ranks:
        for affil in participant.abstract.get_affiliations():
            if (not affil) or (affil.institute == '(please choose)'):
                problems.append('Please choose/fill in the institute for Affiliation %i.' %affil.key)
            if affil.country == '(please choose)':
                problems.append('Please choose the country for Affiliation %i.' %affil.key)
            if not affil.street:
                problems.append('Please provide a street for Affiliation %i.' %affil.key)
            if not affil.city:
                problems.append('Please provide a city for Affiliation %i.' %affil.key)

    # check abstract
    if not participant.abstract.category or participant.abstract.category == '(please choose)':
        problems.append('Please choose a category for your abstract.')
    if not participant.abstract.title:
        problems.append('Please provide a title for your abstract.')
    if not participant.abstract.content:
        problems.append('Please provide some content for your abstract.')
    if config.submission.require_figure_caption and participant.abstract.img_use and not participant.abstract.img_caption:
        problems.append('Please provide a caption for your figure.')

    db_session.close()

    return problems

#########################
###  export abstract  ###
#########################

def build_affiliation(affil):
    return ', '.join([field for field in [affil.department, affil.institute, affil.street, affil.postal_code, affil.city, config.IOC_code[affil.country]] if field])

def build_authaffil(participant, format='tex'):

    if format == 'tex':
        mainauthor_format = '\\textbf{%s}'
        marker_format = '%s\\textsuperscript{%s}'
        affil_format = '\\textsuperscript{%i}%s\n'
    elif format == 'html':
        mainauthor_format = '<strong>%s</strong>'
        marker_format = '%s<sup>%s</sup>'
        affil_format = '<sup>%i</sup>%s<br />'
    else:
        raise ValueError('unkown format %s' %format)

    title_sep = '\\vspace{0.1cm} \n'
    add_affil_marker = len(participant.abstract.affiliations) - 1

    # authors
    if len(participant.abstract.authors) == 1:
        authors_line = mainauthor_format %participant.abstract.get_mainauthor().fullname
        add_affil_marker = False
    else:
        authors = participant.abstract.get_authors()
        mainauthor = participant.abstract.get_mainauthor()
        authors.remove(mainauthor)

        if add_affil_marker:
            author_labels = [marker_format %(author.fullname, ','.join(map(str, author.affiliation_keys))) for author in authors]
            mainauthor_label = mainauthor_format %mainauthor.fullname
            mainauthor_label = marker_format %(mainauthor_label, ','.join(map(str, mainauthor.affiliation_keys)))
        else:
            author_labels = [author.fullname for author in authors]
            mainauthor_label = mainauthor_format %mainauthor.fullname

        authors_line = ', '.join([mainauthor_label]+author_labels[:-1]) + ' and ' + author_labels[-1]

    if format == 'tex':
        authoraffil = authors_line + '\n' + title_sep + '\n'
    elif format == 'html':
        authoraffil = '<p class="text-center">' + authors_line + '</p>\n'

    # affiliations
    affils = []
    for affil in participant.abstract.affiliations:
        if add_affil_marker:
            affils.append(affil_format %(affil.key, build_affiliation(affil)))
        else:
            affils.append(build_affiliation(affil))

    for affil in affils:
        if format == 'tex':
            authoraffil += affil + '\n' + title_sep + '\n'
        elif format == 'html':
            authoraffil += '<p class="text-center">' + affil + '</p>\n'

    return authoraffil

def write_tex(ID, mask_email=False):

    ## create/check target_dir
    target_dir = os.path.join(config.paths.abstracts, ID)
    if not os.path.isdir(target_dir):
        os.makedirs(target_dir)

    ## get participant
    db_session = create_session()

    if ID == 'example':
        from ..abstract_example import participant

        # search figure in instance preferences
        figurename = ''
        if config.prefs_instance:
            for fname in os.listdir(config.prefs_instance):
                if fname.startswith('abstract_example_figure.') and (fname.rsplit('.', 1)[1].lower() in config.forms.ALLOWED_EXTENSIONS):
                    figurename = os.path.join(config.prefs_instance, fname)
                    break

        # search figure in defaults preferences
        if not figurename:
            for fname in os.listdir(config.prefs_default):
                if fname.startswith('abstract_example_figure.') and (fname.rsplit('.', 1)[1].lower() in config.forms.ALLOWED_EXTENSIONS):
                    figurename = os.path.join(config.prefs_default, fname)
                    break

        if figurename:
            copy(figurename, os.path.join(target_dir, 'figure.'+fname.rsplit('.', 1)[1].lower()))

    else:
        participant = db_session.query(Participant).get(ID)

    ## load template
    fname = os.path.join(config.paths.BoA,'abstract_template_%s.tex' %participant.rank)
    if not os.path.isfile(fname):
        fname = os.path.join(config.paths.BoA,'abstract_template.tex')

    fd = codecs.open(fname, encoding='utf-8')
    tex = fd.read()
    fd.close()

    ## build authoraffil
    authoraffil = build_authaffil(participant)

    # invited fields
    name = '%s %s' %(participant.title, participant.fullname)
    name = name.strip(' ,')
    affil = participant.abstract.get_affiliations()[0]
    institute = affil.institute
    department = affil.department
    address = '%s %s, %s' %(affil.postal_code, affil.city, affil.street)
    address = address.strip(' ,')

    # check if empty
    institute = institute if institute else '\\quad'
    department = department if department else '\\quad'
    address = address if address else '\\quad'

    params = {
        'type' : participant.abstract.type,
        'category' : participant.abstract.category,
        'img_use' : ('false', 'true')[participant.abstract.img_use],
        'img_width' : float(participant.abstract.img_width)/100,
        'img_caption' : participant.abstract.img_caption,
        'time' : participant.abstract.time_slot.replace('-', '--') if  participant.abstract.time_slot else '',
        'label' : participant.abstract.label,
        'title' : pandoc.markdown2latex(participant.abstract.title),
        'authoraffil' : authoraffil,
        'abstracttext' : pandoc.markdown2latex(participant.abstract.content),
        # for invited
        'name' : name,
        'institute' : institute,
        'department' : department,
        'address' : address,
        }

    ## insert data
    tex = tex %params

    ## save tex file
    with codecs.open(os.path.join(target_dir, 'abstract.tex'),'w', encoding='utf-8') as fd:
        fd.write(tex)

    db_session.close()

def export_abstract(ID):
    problems = check_abstract(ID)
    if not problems:
        write_tex(ID)
        return 1
    return 0

#################################
###  check texlog for errors  ###
#################################

def check_log(ID):

    # load log file
    with codecs.open(os.path.join(config.paths.abstracts, ID, ID+'.log'), encoding='ISO-8859-15') as fd:
        log = fd.readlines()

    # get first line
    start_line = None
    for iline, line in enumerate(log):
        if line.startswith('! '):
            start_line = iline
            break

    # check if error found
    if not start_line:
        return ''

    # get last line
    while iline < len(log):
        if log[iline].startswith('l.'):
            iline += 2
            while (log[iline] != '\n') and not log[iline].startswith('Here is how much of TeX'):
                iline += 1
            else:
                end_line = iline
        iline += 1

    return ''.join(log[start_line:end_line])

#############################################
###  backup last versions of tex/pdf file ###
#############################################

def cycle_files(ID):

    # keeps last <N_backup_abstracts> versions of tex and pdf file

    # set directory
    abstract_dir = os.path.join(config.paths.abstracts,ID)

    # remove log files
    if os.path.isfile(os.path.join(abstract_dir, 'tex.stdout')):
        os.remove(os.path.join(abstract_dir, 'tex.stdout'))
    if os.path.isfile(os.path.join(abstract_dir, '%s.log' %ID)):
        os.remove(os.path.join(abstract_dir, '%s.log' %ID))

    # check files
    if not os.path.isfile(os.path.join(abstract_dir, ID+'.pdf')):
        return

    tex_files = glob(os.path.join(abstract_dir,'*.tex.*'))

    if tex_files:
        Ntex = max([int(file[-1]) for file in tex_files])
    else:
        Ntex = 0

    # cycle files (remove if > N_backup_abstracts)
    Ntex = min(Ntex+1, config.submission.N_backup_abstracts)
    for ii in range(Ntex,1,-1):
        os.rename(os.path.join(abstract_dir,'abstract.tex.%i' %(ii-1)), os.path.join(abstract_dir,'abstract.tex.%i' %(ii)))
        os.rename(os.path.join(abstract_dir,'%s.pdf.%i' %(ID,ii-1)), os.path.join(abstract_dir,'%s.pdf.%i' %(ID,ii)))

    os.rename(os.path.join(abstract_dir,'abstract.tex'), os.path.join(abstract_dir,'abstract.tex.1'))
    os.rename(os.path.join(abstract_dir,'%s.pdf' %ID), os.path.join(abstract_dir,'%s.pdf.1' %ID))
