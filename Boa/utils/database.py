# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from ..modules import config, database

def get_events():
    """Get events from config and database."""
    db_session = database.create_session()
    events = config.registration.events
    for i in db_session.query(database.Participant.events.distinct()).all():
        for event in i[0].split(','):
            if event and not event in events:
                events.append(event)
    db_session.close()
    return events

def get_ranks(hidden=False):
    """Get ranks from config and database."""
    db_session = database.create_session()
    ranks = [ i[0] for i in db_session.query(database.Participant.rank.distinct()).all() ]
    ranks = set(ranks) | set(config.registration.ranks) | set(config.registration.ranks_invited)
    # remove hidden ranks
    if not hidden:
        ranks = ranks - set(config.registration.ranks_hidden)
    db_session.close()
    return list(ranks)

def get_contributions():
    """Get contributions from config and database."""
    db_session = database.create_session()
    contributions = [ i[0] for i in db_session.query(database.Participant.contribution.distinct()).all() ]
    if not 'Talk' in contributions:
        contributions.append('Talk')
    if not 'Poster' in contributions:
        contributions.append('Poster')
    db_session.close()
    return contributions

def get_IP_statistics():
    db_session = database.create_session()
    perdate = db_session.query(
        database.IPStatistics.date,
        database.func.count(database.IPStatistics.date)
    ).group_by(database.IPStatistics.date).all()
    db_session.close()
    total = db_session.query(database.IPStatistics).group_by(database.IPStatistics.IP).count()
    return perdate + [('total', total)]
