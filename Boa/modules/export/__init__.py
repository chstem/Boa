# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from builtins import str
from codecs import open
import os
import re
from shutil import copy
from subprocess import Popen
from time import localtime

from . import abstract
from . import participant
from . import program

from .. import config
from .. import database
from .. import TexCleaner as tc

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
    with open(filename, 'w', encoding='utf-8') as fd:
        fd.write(data)

##################
###  Invoices  ###
##################

def invoice_data():
    db_session = database.create_session()
    participants = db_session.query(database.Participant)\
        .filter(database.Participant.rank == 'participant')\
        .order_by(database.Participant.lastname)\
        .all()

    data = [(
        'firstname',
        'lastname',
        'title',
        'line1',
        'line2',
        'street',
        'PLZ',
        'city',
        'invoiceNo',
        'taxNo',
        'events',
        'surcharge',
        'earlybird',
        'fee',
    ),]

    for participant in participants:

        # check deadlines
        if config.registration.earlybird:
            earlybird = localtime(participant.time_registered) <= config.registration.earlybird
        else:
            earlybird = False

        if config.registration.surcharge:
            surcharge = localtime() > config.registration.surcharge
        else:
            surcharge = False

        # invoice_number
        if not participant.invoice_number:
            # assign highest invoice_number + 1
            invoice_no = db_session.query(database.Participant).order_by(database.Participant.invoice_number.desc()).first().invoice_number
            invoice_no += 1
            participant.invoice_number = invoice_no
        db_invoice_number = '%04d' %participant.invoice_number
        db_session.commit()

        tax_no = participant.tax_number if participant.tax_number else ''

        # add row
        data.append((
            participant.firstname,
            participant.lastname,
            participant.title,
            participant.address_line1,
            participant.address_line2,
            participant.street,
            participant.postal_code,
            participant.city,
            participant.invoice_number,
            tax_no,
            participant.events,
            surcharge,
            earlybird,
            config.calc_fee(participant),
        ))

    write_csv('invoices_data.csv', data)
    db_session.close()

###################
###  Name Tags  ###
###################

def nametags(cols=2, rows=5, doublesided=True):

    # get all participants
    db_session = database.create_session()
    data = []
    participants = db_session.query(database.Participant).order_by(database.Participant.lastname).all()
    for participant in participants:
        staff = 'staff' if participant.rank == 'staff' else ''
        data.append((participant.firstname, participant.lastname, participant.title, participant.institute, staff))
    db_session.close()

    # fill
    empty = [('', '', '', '', '')]
    tags_per_page = cols*rows
    if tags_per_page:
        N = tags_per_page - len(data)%tags_per_page
        data.extend(empty*N)

    # duplicate entries: repeat every x elements
    if doublesided:
        data2 = []
        for n in range(0, len(data), tags_per_page):
            page = data[n:n+tags_per_page]
            # front side
            data2.extend(page)
            # back side (switch columns)
            switched = []
            for c in range(cols):
                switched = page[c*rows:(c+1)*rows] + switched
            data2.extend(switched)
        data = data2

    # append head
    data = [('firstname', 'lastname', 'title', 'institute', 'staff')] + data

    # write file
    if not os.path.isdir('Name_Tags'):
        os.mkdir('Name_Tags')
        copy(os.path.join(config.module_path, 'Name_Tags', 'Name_Tags.tex'), 'Name_Tags')
    write_csv(os.path.join('Name_Tags', 'name_tags.csv'), data)

    # run pdflatex
    os.chdir('Name_Tags')
    p = Popen(['pdflatex', 'Name_Tags.tex'])
    p.wait()
    os.chdir(config.instance_path)

#######################
###  Poster Badges  ###
#######################

tex_badges = r'''\documentclass[a4paper,landscape,12pt]{letter}
\usepackage{ticket}
\unitlength=1mm
\hoffset=-10mm
\voffset=-16mm
\ticketNumbers{3}{2}
\ticketSize{90}{90}     %% unitlength mm
\ticketDistance{0}{0}   %% unitlength mm
\usepackage{graphicx,palatino,marvosym}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{xcolor}
\renewcommand{\ticketdefault}{}%%
\makeatletter
\@emptycrossmarkfalse
\@cutmarkfalse
\@boxedtrue
\makeatother
\newcommand{\badge}[2]{\ticket{%%
    \put(15,35){\scalebox{8}{\textbf{#2}}}
    \put(10,10){\begin{minipage}[t]{70mm} \flushleft \large{#1} \end{minipage}}
}}
\begin{document}
%s
\end{document}
'''

def poster_badges():
    #TODO: sort by Session
    db_session = database.create_session()
    participants = db_session.query(database.Participant).join(database.Abstract)\
        .filter(database.Participant.contribution == 'Poster')\
        .order_by(database.Abstract.label)
    badges = ['\\badge{%s}{%s}' %(p.fullname,p.abstract.label) for p in participants]
    with open('posterbadges.tex', 'w', encoding='utf-8') as fd:
        fd.write(tex_badges %'\n'.join(badges))
    db_session.close()
    p = Popen(['pdflatex', 'posterbadges.tex'])
    p.wait()
