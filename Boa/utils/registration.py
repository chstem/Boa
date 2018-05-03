# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import os
from random import randint
from time import localtime

from ..modules import config, database
from ..modules.Email import sendmail, render_mail

def create_new_ID():

    # get existing IDs
    db_session = database.create_session()
    IDs = [ entry[0] for entry in db_session.query(database.Participant.ID).all() ]
    IDs.append('example')
    db_session.close()

    # generate ID
    alphabet_length = len(config.ID.alphabet)
    while True:
        ID = ''
        for ii in range(config.ID.length):
            ID += config.ID.alphabet[randint(0,alphabet_length-1)]
        if not (ID in IDs):
            break

    return ID

def registration_isclosed():

    # check config setting
    if not config.registration.enabled:
        return True

    # check start
    if config.registration.start and config.registration.start > localtime():
        return 'notyet'

    # check deadline
    if config.registration.deadline and config.registration.deadline < localtime():
        return 'deadline'

    # check number of participants
    if config.registration.max_participants:
        db_session = database.create_session()
        participants_registered = db_session.query(database.Participant).filter(database.Participant.rank == 'participant').count()
        db_session.close()
        if participants_registered >= config.registration.max_participants:
            return 'full'

    return False

#############################
###  notification emails  ###
#############################

def send_reg_mail(para):

    # add synonym
    para['recipient'] = para['participant']

    # get registration fee
    para['fee'] = config.calc_fee(para['participant'])

    # send mail to newly registered participant
    sendmail(
        subject = '%s %s: Registration confirmed' %(config.conference.conference_acronym, config.conference.year),
        message = render_mail('confirm_registration.html', **para),
        fromaddr = config.mail.registration_email,
        to_list = [para['participant'].email,],
        mailformat='html',
        ParticipantID = para['participant'].ID,
    )
