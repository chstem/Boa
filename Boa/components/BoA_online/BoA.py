# -*- coding: utf-8 -*-
##################################################
###  Book of Abstract - Online version (html)  ###
##################################################

from __future__ import unicode_literals
from flask import abort, Blueprint, render_template, redirect, session, url_for

from ...modules import config, database, export, pandoc
from ...modules.cache import cache
from ...utils import create_parameter_dict

blueprint = Blueprint('BoAonline', __name__, url_prefix='/BoA', template_folder='templates')

@blueprint.route('/abstract/<ID>/')
@cache.memoize(3600)
def abstract(ID):
    """Show abstract as HTML."""

    if ID == 'example':
        from ...modules.abstract_example import participant
    else:
        db_session = database.create_session()
        # check if ID matches any abstract label
        abstract = db_session.query(database.Abstract).filter(database.Abstract.label == ID).first()
        if not abstract:
            # use ID as participant ID
            participant = db_session.query(database.Participant).get(ID)
        else:
            participant = abstract.participant
            ID = participant.ID

        if not participant:
            db_session.close()
            abort(404)

    # build HTML abstract
    para = create_parameter_dict()
    content = pandoc.markdown2html(participant.abstract.content)
    ind = content.rfind('<div class="footnotes">')
    para['time_slot'] = participant.abstract.time_slot
    para['category'] = participant.abstract.category
    para['title'] = pandoc.markdown2html(participant.abstract.title)
    para['authaffil'] = export.abstract.build_authaffil(participant, format='html')
    para['content'] = content[:ind] if ind >= 0 else content
    para['footnotes'] = content[ind:] if ind >= 0 else ''
    para['img_use'] = participant.abstract.img_use
    para['img_caption'] = pandoc.markdown2html(participant.abstract.img_caption)
    para['ID'] = ID
    para['label'] = participant.abstract.label

    if ID != 'example':
        db_session.close()

    return render_template('show_abstract.html', **para)

def get_sessions(db_session=None):
    if _close_session:
        db_session.close()
    return session_list

@blueprint.route('/abstractlist/')
@cache.memoize(3600)
def abstract_list():
    """List all abstracts."""
    para = create_parameter_dict()
    db_session = database.create_session()
    sessions = db_session.query(database.Session).order_by(database.Session.time_slot).all()
    para['sessions'] = []
    for session in sessions:
        abstracts = session.get_abstracts()
        if not abstracts:
            continue
        session_dict = {
            'name' : session.name,
            'time' : session.time_slot,
            'abstracts' : abstracts,
        }
        para['sessions'].append(session_dict)
    html = render_template('BoA_abstract_list.html', **para)
    db_session.close()
    return html

@blueprint.route('/')
@cache.memoize(3600)
def TOC():
    """Book of Abstracts in HTML format."""
    db_session = database.create_session()
    para = create_parameter_dict()
    para['sections'] = []

    # get all Talks
    talks = db_session.query(database.Abstract).join(database.Participant)\
        .filter(database.Participant.contribution == 'Talk')\
        .order_by(database.Abstract.label)

    para['sections'].append({
        'name' : 'Talks',
        'abstracts' : [talk for talk in talks if not talk.label in (None, '', 'plenary')],
    })

    # get all Posters
    posters = db_session.query(database.Abstract).join(database.Participant)\
        .filter(database.Participant.contribution == 'Poster')\
        .order_by(database.Abstract.label)

    para['sections'].append({
        'name' : 'Poster',
        'abstracts' : [p for p in posters if not p.label in (None, '')],
    })

    db_session.close()

    return render_template('BoA.html', **para)
