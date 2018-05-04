#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import argparse
import os

# avoid logger setup for Boa.app during import
os.environ['FLASK_ENV'] = 'config'

### top-level parser
parser = argparse.ArgumentParser(description='Boa command line interface.')
subparsers = parser.add_subparsers()

### initialise instance
def init(args):
    if args.cmd == 'files':
        from Boa.modules.config import module_path, instance_path, paths
        from shutil import copy, copytree

        # copy config.py
        if os.path.isfile(os.path.join(instance_path, 'preferences', 'config.py')):
            print('config.py already exists, skipping')
        else:
            print('creating preferences/config.py')
            if not os.path.isdir(os.path.join(instance_path, 'preferences')):
                os.mkdir(os.path.join(instance_path, 'preferences'))
            copy(os.path.join(module_path, 'preferences', 'config.py'), os.path.join(instance_path, 'preferences', 'config.py'))

        # copy LaTeX template files
        if os.path.isdir(paths.BoA):
            print('LaTeX directory already exists, skipping')
        else:
            print('creating', paths.BoA)
            copytree(os.path.join(module_path, 'BoA'), paths.BoA)

        # create directories
        if not os.path.isdir('mail_templates'):
            os.mkdir('mail_templates')
        if not os.path.isdir('static'):
            os.mkdir('static')

    elif args.cmd == 'database':
        # (re)initialise database tables
        if args.tables == 'all':
            databases = ['Data', 'Meta', 'Mail', 'feedback']
        elif args.tables == 'core':
            databases = ['Data', 'Meta', 'Mail']
        else:
            databases = [args.tables]

        import Boa.modules.database as db
        from importlib import import_module
        for table in databases:
            try:
                Base = getattr(db, 'Base'+table.capitalize())
                Base.metadata.drop_all(db.engine)
                Base.metadata.create_all(db.engine)
            except AttributeError:
                # component table
                component = import_module('.'+table, 'Boa.components')
                component.metadata.drop_all(db.engine)
                component.metadata.create_all(db.engine)

parser_init = subparsers.add_parser('init', help='initialise instance')
parser_init.add_argument('cmd', choices=['files', 'database'])
parser_init.add_argument('-t', '--tables',
                         help='select database tables to (re)initialise',
                         default='core',
                         choices=['all', 'core', 'data', 'stats', 'mail', 'feedback'])
parser_init.set_defaults(func=init)

### run server
def run(args):
    # run server in testing mode
    os.environ['FLASK_ENV'] = 'development'
    from Boa import app, config
    app.config['TRAP_BAD_REQUEST_ERRORS'] = False
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    config.registration.reject_double_registration = False
    app.run(host='0.0.0.0', port=config.flask.test_port, debug=True, use_evalex=True)

parser_run = subparsers.add_parser('test', help='run server in test/development mode')
parser_run.set_defaults(func=run)

### database exports
def export(args):
    from Boa.modules.config import paths
    from Boa.modules import database as db
    from Boa.modules import export
    from codecs import open
    db_session = db.create_db_session()

    if args.cmd == 'abstract':
        if not args.ID:
            print('abstract ID required')
        else:
            export.write_tex(args.ID, mask_email=args.mask_email)

    elif args.cmd == 'abstracts':
        # export all abstracts
        abstracts = db_session.query(db.Abstract).filter(db.Abstract.is_submitted).all()
        IDs = [abstract.participant.ID for abstract in abstracts]
        for ID in IDs:
            export.write_tex(ID, mask_email=args.mask_email)

    elif args.cmd == 'index':
        export.index()

    elif args.cmd == 'posters':
        # get all poster contributions
        participants = db_session.query(db.Participant).join(db.Abstract)\
            .filter(db.Participant.contribution == 'Poster')\
            .order_by(db.Abstract.label)\

        # filter submitted abstracts
        participants = [p for p in participants.all() if participant.abstract_submitted]

        # create Poster.tex
        with open(os.path.join(paths.BoA, 'Posters.tex'), 'w', encoding='utf-8') as fd:
            fd.writelines(['\\includeabstract{%s}\n' %p.ID for p in participants])

    elif args.cmd == 'talks':
        # get all talk contributions
        raise NotImplementedError

    elif args.cmd == 'invoices':
        # export invoice data
        raise NotImplementedError

    elif args.cmd == 'nametags':
        # export data for name tags
        raise NotImplementedError

    elif args.cmd == 'posternumbers':
        # numbers for poster walls
        raise NotImplementedError

    db_session.close()

parser_export = subparsers.add_parser('export', help='database exports')
parser_export.add_argument('cmd', choices=[
    'abstract', 'abstracts',
    'index', 'posters', 'talks',
    'invoices', 'nametags', 'posternumbers',])
parser_export.add_argument('-d', '--ID', help='abstract ID', default='')
parser_export.add_argument('--mask_email', help='replace @ with [at]', action='store_true')
parser_export.set_defaults(func=export)

### participant management
def part(args):
    from Boa.modules.config import paths
    from Boa.modules import database as db
    from Boa.modules import export
    db_session = db.create_session()

    if args.cmd == 'delete':
        participant = db_session.query(Participant).get(args.ID)
        if not participant:
            print('ID {} not found'.format(args.ID))
            return
        print('creating JSON backup')
        export.export_to_json(args.ID)
        print('deleting abstract directory')
        if os.path.isdir(os.path.join(paths.abstracts,ID)):
            from shutil import rmtree
            rmtree(os.path.join(paths.abstracts,ID))
        print('deleting from database')
        db_session.delete(participant)
        try:
            db_session.commit()
        except:
            db_session.rollback()
            db_session.close()
            raise

    elif args.cmd == 'restore':
        export.import_json(args.ID)

    elif args.cmd == 'send_reg_mail':
        participant = db_session.query(Participant).get(args.ID)
        if not participant:
            print('ID {} not found'.format(args.ID))
            return
        from Boa import app
        from Boa.utils import create_parameter_dict, send_reg_mail
        para = create_parameter_dict()
        with app.app_context():
            para['participant'] = participant
            para['ID'] = args.ID
            print('sending registration confirmed email to', participant.fullname, participant.ID, participant.email)
            send_reg_mail(para, notify_admin=False)

    elif args.cmd == 'send_paid_mail':
        raise NotImplementedError

    db_session.close()

parser_part = subparsers.add_parser('participant', help='manage participants')
parser_part.add_argument('cmd', choices=['delete', 'restore', 'send_reg_mail', 'send_paid_mail'])
parser_part.add_argument('ID', help='participant IDs')
parser_part.set_defaults(func=part)

### collect talk abstracts
def collect_talks(args):
    from Boa.modules import database as db
    from Boa.modules.config import paths
    from Boa.modules.export import export_abstract
    from Boa.utils import make_preview
    from subprocess import Popen

    db_session = db.create_session()
    participants = db_session.query(db.Participant).join(db.Abstract)\
        .filter(db.Participant.contribution == 'Talk')\
        .order_by(db.Abstract.label)\
        .all()
    IDs = []

    for participant in participants:
        if not participant.abstract_submitted:
            print('missing abstract for', participant.contribution, participant.ID, participant.fullnamel)
            continue
        print(participant.contribution, participant.ID, participant.fullnamel, participant.abstract.title)
        IDs.append(os.path.join(paths.abstracts, participant.ID, participant.ID+'.pdf'))

        # create preview pdf
        make_preview(participant.ID, halt_latex=False)

    db_session.close()
    Popen(['pdfjam',] + IDs + ['-o', os.path.join(paths.BoA, 'Talks.pdf')])
    print('Output:', os.path.join(paths.BoA, 'Talks.pdf'))

parser_collect = subparsers.add_parser('collect_talks', help='collect all submitted talk abstracts in a single pdf')
parser_part.set_defaults(func=collect_talks)

### parse args and run command
args = parser.parse_args()
if hasattr(args, 'func'):
    args.func(args)
else:
    parser.print_help()
