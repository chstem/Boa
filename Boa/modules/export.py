# -*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function
from builtins import str
import codecs
from glob import glob
import os
import re
from shutil import copy

from . import config
from .database import *
from . import pandoc
from . import TexCleaner as tc

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
        from modules.abstract_example import participant
        copy('preferences/abstract_example_figure.pdf', os.path.join(target_dir,'figure.pdf'))
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
        'time' : participant.abstract.time_slot.replace('-', '--'),
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

##############################
###  Sessions and Program  ###
##############################

def talks():
    db_session = create_session()
    sessions = db_session.query(Session).filter(Session.type == 'talk').order_by(Session.time_slot).all()

    with open(os.path.join(config.paths.BoA, 'Talks.tex'), 'w', encoding='utf-8') as fd:
        for session in sessions:

            abstracts = session.get_abstracts()
            if not abstracts:
                continue

            fd.write('\n')
            fd.write('%%%%{:s}\n'.format(session.name))
            fd.write('\\phantomsection\n')
            fd.write('\\addcontentsline{{toc}}{{subsubsection}}{{{:s}}}\n'.format(session.name))
            fd.write('\n')

            for abstract in abstracts:
                fd.write('%% {:s}: {:s}\n'.format(abstract.category, abstract.title))
                fd.write('\\phantomsection\n')
                fd.write('\\addcontentsline{{toc}}{{paragraph}}{{{:s} : {:s}}}\n'.format(abstract.time_slot, abstract.participant.fullnamel))
                fd.write('\\includeabstract{{{:s}}}\n'.format(abstract.participant_id))
                fd.write('\n')

    db_session.close()

def posters():
    # TODO: group by poster session
    # get all poster contributions
    db_session = create_session()
    participants = db_session.query(Participant).join(Abstract)\
        .filter(Participant.contribution == 'Poster')\
        .order_by(Abstract.label)\

    # filter submitted abstracts
    participants = [p for p in participants.all() if p.abstract_submitted]

    # create Poster.tex
    with open(os.path.join(config.paths.BoA, 'Posters.tex'), 'w', encoding='utf-8') as fd:
        fd.writelines(['\\includeabstract{%s}\n' %p.ID for p in participants])

    db_session.close()

def timetable():

    def writeline(fd, line):
        fd.write(8*' ')     # indentation
        fd.write(line)
        fd.write('\\\\\n')  # newline

    db_session = create_session()
    sessions = db_session.query(Session).order_by(Session.time_slot).all()
    with open(os.path.join(config.paths.BoA, 'Timetable.tex'), 'w', encoding='utf-8') as fd:

        # head
        fd.write('\\begin{center}\n')
        fd.write('    \\setlength{\\extrarowheight}{.5em}\n')
        fd.write('    \\large\n')
        fd.write('    \\begin{tabular}{cl}\n')

        # sessions
        for session in sessions:
            if session.type == 'talk':
                abstracts = session.get_abstracts()
                if len(abstracts) == 1:
                    title = '{} {}'.format(session.name, abstracts[0].participant.titlename)
                    writeline(fd, '{:s} & \\textbf{{{:s}}}'.format(abstracts[0].time_slot, title))
                elif abstracts:
                    writeline(fd, '{:s} & \\textbf{{{:s}}}'.format(session.time_slot, session.name))
                    for abstract in abstracts:
                        # name + institute
                        line = '{:s} ({:s})'.format(abstract.participant.titlename, abstract.participant.institute)
                        # parbox
                        line = '\\parbox[t]{{0.6\\textwidth}}{{\\raggedright {:s}}}'.format(line)
                        # add time
                        line = '{{{:s}}} : {:s}'.format(abstract.time_slot, line)
                        # hyperref
                        line = ' \\hyperref[{:s}]{{{:s}}}'.format(abstract.participant_id, line)
                        # tabular
                        line = '    & \\normalsize ' + line
                        # write to file
                        writeline(fd, line)
            else:
                writeline(fd, '{:s} & \\textbf{{{:s}}}'.format(session.time_slot, session.name))

        # foot
        fd.write('    \\end{tabular}\n')
        fd.write('\\end{center}\n')

    db_session.close()


######################################
###  Author and Participant Index  ###
######################################

def index():
    class Author():
        def __init__(self, name, participant=False):
            self.name = name
            self.participant = participant
            self.contributions = []
            self.coauthor = []

        def makeline(self):
            # name (bold for participants)
            if self.participant:
                line = '\\textbf{%s}' %self.name
            else:
                line = self.name
            # own contribution (bold)
            if self.contributions:
                line += ', \\textbf{\\labelcpageref{%s}}' %','.join(self.contributions)
            # coauthor
            if self.coauthor:
                line += ', \\labelcpageref{%s}' %(','.join(self.coauthor))
            line += '\\\\\n'
            return line

        def __eq__(self, name):
            return self.name == name

    IndexList = []
    # get authors from database
    db_session = create_session()
    participants = db_session.query(Participant).all()

    for participant in participants:

        ## add participant
        name = participant.fullnamel

        # get/create Author instance
        try:
            iauth = IndexList.index(name)
        except ValueError:
            IndexList.append(Author(name, participant=True))
            iauth = -1

        if participant.contribution != 'None' and not participant.abstract_submitted:
            print('missing abstract for', participant.contribution, participant.ID, participant.fullnamel)
            continue

        ## add Coauthor
        if not participant.abstract_submitted:
            continue
        if participant.contribution == 'None':
            continue

        for author in participant.abstract.authors:
            name = author.fullnamel
            # get/create Author instance
            try:
                iauth = IndexList.index(name)
            except ValueError:
                IndexList.append(Author(name))
                iauth = -1

            # add contribution
            if author.key == 1:
                IndexList[iauth].contributions.append(participant.ID)
            else:
                IndexList[iauth].coauthor.append(participant.ID)

    db_session.close()

    # sort IndexList alphabetically
    IndexList = sorted(IndexList, key=lambda x:x.name.lower())

    # create Index.tex
    index = ''
    last_letter = ''
    for author in IndexList:
        entry = author.makeline()
        first_letter = entry[8] if entry.startswith('\\textbf{') else entry[0]
        if first_letter.upper() != last_letter:
            if last_letter:
                index += '\\\\\n'
            last_letter = first_letter.upper()
            index += '\\textbf{%s}\\nopagebreak\\\\\n' %last_letter
        index += entry

    # write file
    with codecs.open(os.path.join(config.paths.BoA, 'Index.tex'), 'w', encoding='utf-8') as fd:
        fd.write(index)

############################
###  export data to csv  ###
############################

def write_csv(filename, data, separators=';&$+§', escape_tex='%&#_', replace_empty=r'\ '):

    # coerce string
    data = [ list(map(str, row)) for row in data ]

    # find separator not used in data fields
    concat = ''.join([ ''.join(fields) for fields in data ])
    sep = ''
    for s in separators:
        if not s in concat:
            sep = s
            break

    if not sep:
        raise RuntimeError('no suitable separator found')

    # join fields with separator
    data = [ sep.join(fields) for fields in data ]
    data = '\n'.join(data)

    # escape special character for tex
    escape_tex = escape_tex.replace(sep, '')
    if escape_tex:
        data = tc.escape_symbols(data, symbols=escape_tex)

    # replace empty fields
    if replace_empty:
        data = re.sub('%s(?=%s)' %(sep, sep), sep+replace_empty, data)
        #data = data.replace(2*sep, sep+replace_empty+sep)

    # ensure linebreak at end of file
    if not data.endswith('\n'):
        data += '\n'

    # write to file
    with codecs.open(filename, 'w', encoding='utf-8') as fd:
        fd.write(data)

####################################
###  export participant as JSON  ###
####################################

import json

def export_to_json(ID):
    """Export participant from database to JSON."""

    # get participant from database
    db_session = create_session()
    participant = db_session.query(Participant).get(ID)

    if not participant:
        db_session.close()
        return

    # create dict
    data = {
        'Participant':{},
        'Abstract':{},
        'Authors':[],
        'Affiliations':[],
        }

    # Participant
    for key, value in participant.__dict__.items():
        if key.startswith('_'):
            continue
        if key in ('abstract',):
            continue
        data['Participant'][key] = value

    if participant.abstract:

        # Abstract
        for key, value in participant.abstract.__dict__.items():
            if key.startswith('_'):
                continue
            if key in ('authors','affiliations', 'participant_id'):
                continue
            data['Abstract'][key] = value

        # Authors
        for author in participant.abstract.authors:
            data['Authors'].append({})
            for key, value in author.__dict__.items():
                if key.startswith('_'):
                    continue
                if key in ('id', 'abstract_id', 'participant_id'):
                    continue
                data['Authors'][-1][key] = value

        # Affiliations
        for affil in participant.abstract.affiliations:
            data['Affiliations'].append({})
            for key, value in affil.__dict__.items():
                if key.startswith('_'):
                    continue
                if key in ('id', 'abstract_id'):
                    continue
                data['Affiliations'][-1][key] = value

    # store as JSON file
    fname = ID + '.json'
    if not os.path.isdir(config.paths.backup):
        os.mkdir(config.paths.backup)
    with codecs.open(os.path.join(config.paths.backup, fname), 'w', encoding='utf-8') as fd:
        json.dump(data, fd)

    db_session.close()

    # copy figure(s)
    for fname in glob(os.path.join(config.paths.abstracts,ID,'figure.*')):
        ext = fname.rsplit('.', 1)[1].lower()
        copy(fname, os.path.join(config.paths.backup, '%s.%s' %(ID, ext)))

def import_json(ID, change_ID=None):
    """Import participant from a JSON formatted file."""

    # load JSON
    fname = ID + '.json'
    with codecs.open(os.path.join(config.paths.backup, fname), encoding='utf-8') as fd:
        data = json.load(fd)

    # Participant
    participant = Participant(**data['Participant'])

    if change_ID:
        participant.ID = change_ID

    # Abstract
    if data['Abstract']:

        abstract = Abstract(**data['Abstract'])

        authors = []
        for author in data['Authors']:
            authors.append( Author(**author) )

        affiliations = []
        for affil in data['Affiliations']:
            affiliations.append( Affiliation(**affil) )

        abstract.authors = authors
        abstract.affiliations = affiliations
        participant.abstract = abstract

    # add to database
    db_session = create_session()
    try:
        db_session.add(participant)
        db_session.commit()
    except:
        db_session.rollback()
        db_session.close()
        raise

    # restore figure(s)
    for fname in glob(os.path.join(config.paths.backup,ID+'.*')):
        ext = fname.rsplit('.', 1)[1].lower()
        if ext != 'json':
            if not os.path.isdir(os.path.join(config.paths.abstracts,participant.ID)):
                os.mkdir(os.path.join(config.paths.abstracts,participant.ID))
            copy(fname, os.path.join(config.paths.abstracts,participant.ID,'figure.%s' %ext))

    db_session.close()
