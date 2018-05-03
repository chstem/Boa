# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from flask import Blueprint, render_template, request
from glob import glob
import os
from time import strftime, strptime, localtime
from werkzeug import secure_filename

from ...modules import database, config
from ...modules.forms import BaseForm, StringField, validators, FileAllowed, FileField
from ...utils import create_parameter_dict

blueprint = Blueprint('cv_upload', __name__, url_prefix='/cv_upload', template_folder='templates')

#####################
###  preferences  ###
#####################

target_dir = os.path.join(config.instance_path, config.components.CV_upload.folder)
allowed_files = config.components.CV_upload.allowed_files
deadline = config.components.CV_upload.deadline
restrict_events = config.components.CV_upload.restrict_events

if deadline:
    deadline_label = strftime(config.timeformat, deadline)
else:
    deadline_label = ''

########################
###  ChiP CV Upload  ###
########################

class CVupload(BaseForm):

    btest = StringField('', [validators.AnyOf('')])    # Bot Protection

    ID = StringField('ID', [validators.Length(max=config.ID.length), validators.InputRequired()])
    upload = FileField('Upload CV', [FileAllowed(allowed_files, 'File type is not valid.'), validators.InputRequired()])

@blueprint.route('/', methods=['GET', 'POST'])
def cv_upload():

    form = CVupload()
    para = create_parameter_dict(
        success=False,
        deadline=deadline_label,
        allowed_files=', '.join(allowed_files),
        )

    # check deadline
    if deadline and deadline < localtime():
        para['deadline'] = 'past'
        return render_template('cv_upload.html', form=form, **para)

    db_session = database.create_session()

    if form.validate_on_submit():

        # check ID
        ID = form.ID.data
        participant = db_session.query(database.Participant).get(ID)

        if not participant:
            db_session.close()
            form.ID.errors.append('Invalid ID.')
            return render_template('cv_upload.html', form=form, **para)

        # check event participation
        if restrict_events:
            if not [e for e in restrict_events if e in participant.events]:
                form.ID.errors.append('Invalid ID.')
                db_session.close()
                return render_template('cv_upload.html', form=form, **para)

        # create directory
        if not os.path.isdir(target_dir):
            os.mkdir(target_dir)

        # filename and target directory
        fup = request.files['upload']
        filename = secure_filename(fup.filename)
        extension = filename.rsplit('.', 1)[1].lower()
        filename = database.toascii('%s_%s' %(participant.lastname, participant.firstname))

        # delete old file
        for oldfilename in glob(os.path.join(target_dir, filename + '.*')):
            os.remove(oldfilename)

        # save new file
        fup.save(os.path.join(target_dir, '%s.%s' %(filename, extension)))
        para['success'] = True
        db_session.close()

    return render_template('cv_upload.html', form=form, **para)
