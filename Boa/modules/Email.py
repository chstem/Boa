# -*- coding: utf-8 -*-

# Python 2/3 compatibility
from __future__ import unicode_literals
try:
    basestring
except NameError:
    basestring = (str, bytes)

from . import config
from .database import MailHistory, create_session

import os
from subprocess import Popen, PIPE
from smtplib import SMTP_SSL, SMTP
from time import time

from email import encoders
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# For guessing MIME type based on file name extension
import mimetypes

def sendmail(subject, message, fromaddr, to_list=[], cc_list=[], bcc_list=[], mailformat='plain', attachments=[], ParticipantID=None):

    if not config.mail.enable:
        return

    ## check input
    if isinstance(to_list, basestring):
        to_list = to_list.split(',')
    if isinstance(cc_list, basestring):
        cc_list = cc_list.split(',')
    if isinstance(bcc_list, basestring):
        bcc_list = bcc_list.split(',')
    if isinstance(attachments, basestring):
        attachments = [ a.strip() for a in attachments.split(',') ]

    # prepare message
    if not attachments:
        msg = MIMEText(message, mailformat, 'utf-8')
        msg['Subject'] = subject
        msg['From'] = fromaddr
        msg['To'] = ', '.join(to_list)
        msg['cc'] = ', '.join(cc_list)
        msg['bcc'] = ', '.join(bcc_list)

    else:
        # code from docs.python.org (email examples)

        outer = MIMEMultipart()
        outer['Subject'] = subject
        outer['From'] = fromaddr
        outer['To'] = ', '.join(to_list)
        outer['cc'] = ', '.join(cc_list)
        outer['bcc'] = ', '.join(bcc_list)
        outer.attach(MIMEText(message, mailformat, 'utf-8'))

        for filename in attachments:

            if not os.path.isfile(filename):
                continue

            # Guess the content type based on the file's extension.  Encoding
            # will be ignored, although we should check for simple things like
            # gzip'd or compressed files.
            ctype, encoding = mimetypes.guess_type(filename)
            if ctype is None or encoding is not None:
                # No guess could be made, or the file is encoded (compressed), so
                # use a generic bag-of-bits type.
                ctype = 'application/octet-stream'
            maintype, subtype = ctype.split('/', 1)

            # create MIME object for file
            if maintype == 'text':
                fp = open(filename)
                # Note: we should handle calculating the charset
                msg = MIMEText(fp.read(), _subtype=subtype)
                fp.close()
            elif maintype == 'image':
                fp = open(filename, 'rb')
                msg = MIMEImage(fp.read(), _subtype=subtype)
                fp.close()
            elif maintype == 'audio':
                fp = open(filename, 'rb')
                msg = MIMEAudio(fp.read(), _subtype=subtype)
                fp.close()
            else:
                fp = open(filename, 'rb')
                msg = MIMEBase(maintype, subtype)
                msg.set_payload(fp.read())
                fp.close()
                # Encode the payload using Base64
                encoders.encode_base64(msg)

            # Set the filename parameter
            msg.add_header('Content-Disposition', 'attachment', filename=os.path.basename(filename))
            outer.attach(msg)

        msg = outer

    # add message to database
    if config.mail.enable_history:
        session = create_session()
        mail = MailHistory(
            ParticipantID = ParticipantID,
            subject = subject,
            message = message,
            fromaddr = fromaddr,
            to_list = msg['To'],
            cc_list = msg['cc'],
            bcc_list = msg['bcc'],
            mailformat = mailformat,
            attachments = ', '.join(attachments),
            success = False,
            time = time(),
            )
        try:
            session.add(mail)
            session.commit()
        except:
            session.rollback()
            session.close()
            raise

    # send the mail(s)
    if config.mail.SENDMAIL.upper() == 'SMTP':

        if config.mail.SMTPSecure.upper() == 'SSL':
            SMTP_connection = SMTP_SSL(config.mail.SMTPServer,config.mail.SMTPPort)
        else:
            SMTP_connection = SMTP(config.mail.SMTPServer,config.mail.SMTPPort)

        #SMTP_connection.set_debuglevel(True)

        if config.mail.SMTPSecure.upper() == 'STARTTLS':
            SMTP_connection.starttls()
            SMTP_connection.ehlo()

        SMTP_connection.login(config.mail.SMTPUsername, config.mail.SMTPPassword)
        SMTP_connection.sendmail(fromaddr, to_list+cc_list+bcc_list, msg.as_string())
        SMTP_connection.quit()

    else:

        # use the server's sendmail program
        p = Popen([config.mail.SENDMAIL, '-t', '-oi'], stdin=PIPE)
        p.communicate(msg.as_string().encode())

    # mark mail as successfully send
    if config.mail.enable_history:
        mail.success = True
        try:
            session.commit()
        except:
            session.rollback()
            session.close()
            raise

        session.close()

#from flask import render_template_string
from jinja2 import Environment, FileSystemLoader, select_autoescape
_searchpaths = [os.path.join(config.module_path, 'mail_templates')]
if config.is_instance:
    _searchpaths.insert(0, os.path.join(config.instance_path, 'mail_templates'))
env = Environment(
    loader = FileSystemLoader(_searchpaths),
    autoescape = select_autoescape(['html', 'xml'])
)
from flask import url_for
env.globals.update(url_for=url_for)

def render_mail(template_file, **context):
    """Search template file in instance and module."""
    template = env.get_template(template_file)
    return template.render(**context)
