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

@blueprint.route('/abstract/<ID>')
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
    para['authaffil'] = export.build_authaffil(participant, format='html')
    para['content'] = content[:ind] if ind >= 0 else content
    para['footnotes'] = content[ind:] if ind >= 0 else ''
    para['img_use'] = participant.abstract.img_use
    para['img_caption'] = pandoc.markdown2html(participant.abstract.img_caption)
    para['ID'] = ID

    if ID != 'example':
        db_session.close()

    return render_template('show_abstract.html', **para)

@blueprint.route('/abstractlist/')
@cache.memoize(3600)
def abstract_list():
    """List all abstracts."""

    para = create_parameter_dict()
    db_session = database.create_session()

    # contributed Talks
    talks = db_session.query(database.Abstract).join(database.Participant)\
        .filter(database.Participant.contribution == 'Talk')\
        .filter(database.Abstract.label != None)\
        .order_by(database.Abstract.label)
    talks = [t for t in talks if t.is_submitted]
    para['talks'] = talks

    # Poster
    poster = db_session.query(database.Abstract).join(database.Participant)\
        .filter(database.Participant.contribution == 'Poster')\
        .filter(database.Abstract.label != None)\
        .order_by(database.Abstract.label)
    poster = [p for p in poster if p.is_submitted]
    para['poster'] = poster

    html = render_template('BoA_abstract_list.html', **para)
    db_session.close()

    return html

@blueprint.route('/')
@cache.memoize(3600)
def TOC():
    """Book of Abstracts in HTML format."""

    para = create_parameter_dict()
    db_session = database.create_session()

    # get all Talks
    talks = db_session.query(database.Abstract).join(database.Participant)\
        .filter(database.Participant.contribution == 'Talk')\
        .order_by(database.Abstract.label)
    para['talks'] = [talk for talk in talks if not talk.label in (None, '', 'plenary')]

    # get all Posters
    posters = db_session.query(database.Abstract).join(database.Participant)\
        .filter(database.Participant.contribution == 'Poster')\
        .order_by(database.Abstract.label)
    para['poster'] = [p for p in posters if not p.label in (None, '')]

    db_session.close()

    return render_template('BoA.html', **para)

@blueprint.route('/Greetings/')
def Greetings():
    para = create_parameter_dict()
    return render_template('Greetings.html', **para)
