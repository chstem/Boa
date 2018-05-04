# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from past.builtins import basestring
import logging
import os
import sys

from . import config, Email

# create directory
if not os.path.isdir('logs'):
    os.mkdir('logs')

## log to rotating files
from logging.handlers import RotatingFileHandler
file_handler = RotatingFileHandler('logs/app.log', maxBytes=1024**2, backupCount=5)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s '
    '[in %(pathname)s:%(lineno)d]'
))

class SendmailHandler(logging.Handler):
    def __init__(self, app, fromaddr, toaddrs, subject):
        logging.Handler.__init__(self)
        self.app = app
        self.fromaddr = fromaddr
        if isinstance(toaddrs, basestring):
            toaddrs = [toaddrs]
        self.toaddrs = toaddrs
        self.subject = subject
    def emit(self, record):
        try:
            from email.utils import formatdate
            msg = self.format(record)
            msg = "From: %s\r\nTo: %s\r\nSubject: %s\r\nDate: %s\r\n\r\n%s" % (
                            self.fromaddr,
                            ",".join(self.toaddrs),
                            self.subject,
                            formatdate(), msg)
            Email.sendmail(self.subject, msg, self.fromaddr, to_list=self.toaddrs)
        except:
            self.app.logger.warning('failed sending error mail')
            self.app.logger.warning(sys.exc_info())
            self.handleError(record)

def get_mail_handler(app):
    mail_handler = SendmailHandler(
        app,
        fromaddr = config.mail.registration_email,
        toaddrs = config.mail.error_email,
        subject = 'Boa: Error occured'
        )
    mail_handler.setLevel(logging.ERROR)
    mail_handler.setFormatter(logging.Formatter('''
        Message type:       %(levelname)s
        Location:           %(pathname)s:%(lineno)d
        Module:             %(module)s
        Function:           %(funcName)s
        Time:               %(asctime)s

        Message:

        %(message)s
    '''))
    return mail_handler
