# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from unicodedata import normalize

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sqlalchemy import Column, Integer, BigInteger, String, Unicode, UnicodeText, Boolean, ForeignKey
from sqlalchemy import func, or_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exc import NoSuchColumnError

from .config import database as db_config
from .config import ID, submission

if db_config.driver == 'mysql':
    engine = create_engine('mysql://%s:%s@%s/%s?charset=utf8' %(db_config.user, db_config.password, db_config.host, db_config.name), pool_recycle=3600)
    collation = 'utf8_bin'
else:
    engine = create_engine(db_config.driver, pool_recycle=3600)
    collation = ''

def toascii(ustr):
    return normalize('NFKD',ustr).encode('ascii', 'ignore')

create_session = sessionmaker(bind=engine)

#######################################
###  Participant and Abstract Data  ###
#######################################

BaseData = declarative_base()

class Participant(BaseData):
    __tablename__ = 'participants'

    ID = Column(String(ID.length), unique=True, nullable=False, primary_key=True)

    firstname = Column(Unicode(100, collation=collation), nullable=False)
    lastname = Column(Unicode(100, collation=collation), nullable=False)
    title = Column(Unicode(20, collation=collation), nullable=False, default='')
    gender = Column(Unicode(8, collation=collation), nullable=True, default=None)
    email = Column(String(80))

    institute = Column(Unicode(100, collation=collation), nullable=False, default='')
    department = Column(Unicode(100, collation=collation), nullable=False, default='')
    address_line1 = Column(Unicode(100, collation=collation), nullable=False, default='')
    address_line2 = Column(Unicode(100, collation=collation), nullable=False, default='')
    street = Column(Unicode(100, collation=collation), nullable=False, default='')
    postal_code = Column(String(10), nullable=False, default='')
    city = Column(Unicode(100, collation=collation), nullable=False, default='')
    country = Column(String(100), nullable=False, default='')

    contribution = Column(String(10), default='None', nullable=False)
    events = Column(String(100), nullable=False, default='')
    paid = Column(Boolean, default=False, nullable=False)
    rank = Column(Unicode(20), default='participant', nullable=False)
    payment_confirmed = Column(BigInteger, default=None, nullable=True)
    time_registered = Column(BigInteger, default=None, nullable=True)
    invoice_number = Column(Integer, default=None, unique=True)
    tax_number = Column(String(20), default=None)
    halt_latex_on_error = Column(Boolean, default=True, nullable=False)

    abstract = relationship('Abstract', uselist=False, backref='participant', cascade='all, delete')

    @property
    def fullnamel(self):
        return '%s, %s' %(self.lastname, self.firstname)

    @property
    def fullname(self):
        return '%s %s' %(self.firstname, self.lastname)

    @property
    def titlename(self):
        if self.title in ('Dr.', 'Prof.'):
            return '%s %s %s' %(self.title, self.firstname, self.lastname)
        else:
            return self.fullname

    @property
    def abstract_submitted(self):
        if not self.abstract:
            return False
        return self.abstract.is_submitted

    def __repr__(self):
        return toascii('<Participant(fullname=\'%s\')>' %self.fullnamel)

class Abstract(BaseData):
    __tablename__ = 'abstracts'

    participant_id = Column(String(ID.length), ForeignKey('participants.ID'), primary_key=True)

    category = Column(String(100))
    title = Column(Unicode(350, collation=collation), nullable=False)
    content = Column(UnicodeText(submission.abstract_length, collation=collation))
    img_use = Column(Boolean, default=False, nullable=False)
    img_width = Column(Integer, default=100, nullable=False)
    img_caption = Column(Unicode(600, collation=collation))
    label = Column(String(10), unique=True, nullable=True)
    time_slot = Column(String(50), nullable=False, default='')

    authors = relationship('Author', backref='abstract', cascade='all, delete, delete-orphan')
    affiliations = relationship('Affiliation', backref='abstract', cascade='all, delete')
    session_id = Column(Integer, ForeignKey('sessions.ID'))
    session = relationship('Session', back_populates='abstracts')

    def get_mainauthor(self):
        for author in self.authors:
            if author.key == 1: return author

    def __repr__(self):
        return toascii('<Abstract(mainauthor=\'%s\')>' %self.get_mainauthor().fullnamel)

    @property
    def type(self):
        return self.participant.contribution

    def get_authors(self):
        # return authors sorted by their key
        return sorted(self.authors, key=lambda author:author.key)

    def get_affiliations(self):
        # return affiliations sorted by their key
        return sorted(self.affiliations, key=lambda affil:affil.key)

    def get_new_author_key(self):
        return self.get_authors()[-1].key + 1

    def get_new_affiliation_key(self):
        return self.get_affiliations()[-1].key + 1

    @property
    def is_submitted(self):
        if not self.category:
            return False
        return True

class Author(BaseData):
    __tablename__ = 'authors'

    id = Column(Integer, primary_key=True)
    abstract_id = Column(String(ID.length), ForeignKey('abstracts.participant_id'))

    key = Column(Integer)
    firstname = Column(Unicode(100, collation=collation), nullable=False)
    lastname = Column(Unicode(100, collation=collation), nullable=False)
    affiliation_keys = Column(String(9), default='', nullable=False)

    @property
    def fullname(self):
        return '%s %s' %(self.firstname, self.lastname)

    @property
    def fullnamel(self):
        return '%s, %s' %(self.lastname, self.firstname)

    def __repr__(self):
        return toascii('<Author(fullname=\'%s\')>' %self.fullnamel)

class Affiliation(BaseData):
    __tablename__ = 'affiliations'

    id = Column(Integer, primary_key=True)
    abstract_id = Column(String(ID.length), ForeignKey('abstracts.participant_id'))

    key = Column(Integer)
    institute = Column(Unicode(100, collation=collation), nullable=False, default='')
    department = Column(Unicode(100, collation=collation), nullable=False, default='')
    street = Column(Unicode(100, collation=collation), nullable=False, default='')
    postal_code = Column(String(10), nullable=False, default='')
    city = Column(Unicode(100, collation=collation), nullable=False, default='')
    country = Column(String(100), nullable=False, default='')

    def __repr__(self):
        return toascii('<Affiliation(institute=\'%s\')>' %self.institute)

class Session(BaseData):
    __tablename__ = 'sessions'
    ID = Column(Integer, primary_key=True)
    name = Column(Unicode(100, collation=collation), nullable=False, default='', unique=True)
    type = Column(String(50, collation=collation), default='')
    time_slot = Column(String(50, collation=collation), nullable=False, default='')
    abstracts = relationship('Abstract', back_populates='session')

#########################
###  Log Sent Emails  ###
#########################

BaseMail = declarative_base()

class MailHistory(BaseMail):
    __tablename__ = 'MailHistory'

    id = Column(Integer, primary_key=True)
    ParticipantID = Column(String(ID.length), nullable=True)
    subject = Column(Unicode(1000, collation=collation))
    message = Column(UnicodeText(collation=collation))
    fromaddr = Column(String(80))
    to_list = Column(String(1000))
    cc_list = Column(String(1000))
    bcc_list = Column(String(1000))
    mailformat = Column(String(10), nullable=False)
    attachments = Column(String(1000))
    success = Column(Boolean, default=False)
    time = Column(BigInteger, default=None, nullable=True)

###################
###  Meta Data  ###
###################

BaseMeta = declarative_base()

class IPStatistics(BaseMeta):
    __tablename__ = 'IPStatistics'

    ID = Column(Integer, primary_key=True)
    IP = Column(String(32))
    date = Column(String(10))
