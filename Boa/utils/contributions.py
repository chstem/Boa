# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from time import localtime

from ..modules import config

def accept_poster():
    return not config.submission.deadline_poster or config.submission.deadline_poster > localtime()

def accept_talks():
    return not config.submission.deadline_talks or config.submission.deadline_talks > localtime()

def get_contribution_choices(participant=None):

    # force choice if ID in config.submission.allow_IDs:
    force_choice = ''
    if participant:
        if participant.ID == 'example':
            return [('None', 'None'), ('Poster', 'Poster'), ('Talk', 'Talk')]
        if participant.ID in config.submission.allow_IDs:
            force_choice = participant.contribution

    # get choices
    choices = [('None', 'None'),]
    if accept_poster() or force_choice == 'Poster':
        choices.append(('Poster', 'Poster'))
    if accept_talks() or force_choice == 'Talk':
        choices.append(('Talk', 'Talk'))
    return choices
