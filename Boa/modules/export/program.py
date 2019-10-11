# -*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function
import codecs
import os

from .. import config
from ..database import *

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
            fd.write('\\addcontentsline{{toc}}{{subsection}}{{{:s}}}\n'.format(session.name))
            fd.write('\n')

            for abstract in abstracts:
                fd.write('%% {:s}: {:s}\n'.format(abstract.category, abstract.title))
                fd.write('\\phantomsection\n')
                fd.write('\\addcontentsline{{toc}}{{subsubsection}}{{{:s} : {:s}}}\n'.format(abstract.time_slot, abstract.participant.fullnamel))
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
