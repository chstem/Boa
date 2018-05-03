# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from unicodedata import normalize
import re

from flask_wtf import FlaskForm as Form
from flask_wtf.file import FileField, FileAllowed
from wtforms import BooleanField, StringField, SelectField, RadioField, IntegerField, TextAreaField, FieldList, FormField, PasswordField, SelectMultipleField
from wtforms import validators, ValidationError, widgets

from . import config

class BaseForm(Form):
    class Meta:
        def bind_field(self, form, unbound_field, options):
            if unbound_field.field_class in (FieldList, FormField):
                return unbound_field.bind(form=form, **options)
            else:
                filters = unbound_field.kwargs.get('filters', None) or []
                filters.append(strip_filter)
                return unbound_field.bind(form=form, filters=filters, **options)
    @classmethod
    def append_field(cls, name, field):
        setattr(cls, name, field)
        return cls

def strip_filter(value):
    if value is not None and hasattr(value, 'strip'):
        return value.strip()
    return value

def validator_alt(selectfield):
    field_flags = ('required',)
    def _validator(form, field):
        if (form.data[selectfield] == 'other'):
            if not field.data:
                raise ValidationError('This field is required if "other" is selected.')
    return _validator

def validator_img():
    field_flags = ('required',)
    def _validator(form, field):
        if form.data['img_use']:
            if not field.data:
                raise ValidationError('This field is required if "Include Figure" is checked.')
    return _validator

def validator_deny_first_selection():
    field_flags = ('required',)
    def _validator(form, field):
        fieldname = 'institute' if 'institute' in field.name else field.name
        if form.data[fieldname] == 'pls_choose':
            raise ValidationError('Choice is not valid.')
    return _validator

def validator_single_email():
    def _validator(form, field):
        if re.search('[ ;,]+', field.data):
            raise ValidationError('Only one email allowed.')
    return _validator

def validator_Gender():
    def _validator(form, field):
        if config.genders and form.data[field.name] == 'pls_choose':
            raise ValidationError('Choice is not valid.')
    return _validator

class MultiCheckboxField(SelectMultipleField):
    """
    A multiple-select, except displays a list of checkboxes.

    Iterating the field will produce subfields, allowing custom rendering of
    the enclosed checkbox fields.
    """
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()

###############
###  Login  ###
###############

class LoginID(BaseForm):

    btest = StringField('', [validators.AnyOf('')])    # Bot Protection

    ID = StringField('ID', [validators.Length(max=config.ID.length), validators.InputRequired()])

class LoginPW(BaseForm):

    btest = StringField('', [validators.AnyOf('')])    # Bot Protection

    password = PasswordField('Password', [validators.InputRequired()])

######################
###  Registration  ###
######################

class Registration(BaseForm):

    btest = StringField('', [validators.AnyOf('')])    # Bot Protection

    firstname = StringField('First Name', [validators.Length(max=100), validators.InputRequired()])
    lastname = StringField('Last Name', [validators.Length(max=100), validators.InputRequired()])
    title = SelectField('Title', [validator_deny_first_selection()], choices=config.forms.title_choices)
    title_alt = StringField('title_alt', [validators.Length(max=100), validator_alt('title')])
    email = StringField('Email', [validators.Email(), validator_single_email(), validators.InputRequired()])
    gender = SelectField('Gender', [validator_Gender()], choices=config.forms.gender_choices, default='pls_choose')

    if config.institute_presets:
        institute = SelectField('Institute/University', [validator_deny_first_selection()], choices=config.forms.institute_choices)
        institute_alt = StringField('Institute/University', [validators.Length(max=100), validator_alt('institute')])
    else:
        institute = StringField('Institute/University', [validators.Length(max=100), validators.InputRequired()])

    address_line1 = StringField('Address Line 1', [validators.Length(max=100)])
    address_line2 = StringField('(optional) Address Line 2', [validators.Length(max=100)])
    department = StringField('(optional) Department', [validators.Length(max=100)])
    street = StringField('Street/Number', [validators.Length(max=100), validators.InputRequired()])
    postal_code = StringField('Postal Code', [validators.Length(max=10), validators.InputRequired()])
    city = StringField('City', [validators.Length(max=100), validators.InputRequired()])
    country = SelectField('Country', choices=config.forms.country_choices, default=config.forms.default_country_id)
    tax_number = StringField('(optional) Tax Number', [validators.Length(max=100)])

    contribution = RadioField('Contribution', [validators.InputRequired()], choices=[('None', 'None'),], default='None')
    accept_rules = BooleanField('I accept the site rules', [validators.InputRequired()])

class RegistrationNoMail(Registration):
    email = StringField('(optional) Email', [validators.Email(), validator_single_email(), validators.Optional()])

class Registration_invited(BaseForm):

    btest = StringField('', [validators.AnyOf('')]) # Bot Protection

    firstname = StringField('First Name', [validators.Length(max=100), validators.InputRequired()])
    lastname = StringField('Last Name', [validators.Length(max=100), validators.InputRequired()])
    title = SelectField('Title', [validator_deny_first_selection()], choices=config.forms.title_choices)
    title_alt = StringField('title_alt', [validators.Length(max=100), validator_alt('title')])
    email = StringField('(optional) Email', [validators.Email(), validator_single_email(), validators.Optional()])
    gender = SelectField('Gender', [validator_Gender()], choices=config.forms.gender_choices, default='pls_choose')
    country = SelectField('Country', choices=config.forms.country_choices, default=config.forms.default_country_id)

    if config.institute_presets:
        institute = SelectField('Institute/University', [validator_deny_first_selection()], choices=config.forms.institute_choices)
        institute_alt = StringField('Institute/University', [validators.Length(max=100), validator_alt('institute')])
    else:
        institute = StringField('Institute/University', [validators.Length(max=100), validators.InputRequired()])
    department = StringField('(optional) Department', [validators.Length(max=100)])

#############################
###  Abstract Submission  ###
#############################

class Author(BaseForm):

    firstname = StringField('First Name', [validators.Length(max=100), validators.InputRequired()])
    lastname = StringField('Last Name', [validators.Length(max=100), validators.InputRequired()])
    affiliations = StringField('Affiliations', [validators.Length(max=100), validators.InputRequired()])

class Affiliation(BaseForm):

    if config.institute_presets:
        institute = SelectField('Institute/University', [validator_deny_first_selection()], choices=config.forms.institute_choices)
        institute_alt = StringField('Institute/University', [validators.Length(max=100), validator_alt('institute')])
    else:
        institute = StringField('Institute/University', [validators.Length(max=100), validators.InputRequired()])

    department = StringField('Department', [validators.Length(max=100)])
    street = StringField('Street/Number', [validators.Length(max=100), validators.InputRequired()])
    postal_code = StringField('Postal Code', [validators.Length(max=10), validators.InputRequired()])
    city = StringField('City', [validators.Length(max=100), validators.InputRequired()])
    country = SelectField('Country', choices=config.forms.country_choices, default=config.forms.default_country_id)

class Abstract(BaseForm):

    btest = StringField('', [validators.AnyOf('')])    # Bot Protection

    authors = FieldList(FormField(Author))
    affiliations = FieldList(FormField(Affiliation))

    contribution = RadioField('Contribution', choices=[('None', 'None'),], default='None')
    category = SelectField('Category')
    title = StringField('Title', [validators.Length(max=300)])
    content = TextAreaField('Abstract')

    img_use = BooleanField('Include Figure')
    img_width = IntegerField('Width (1-100%)', [validators.NumberRange(min=1,max=100)])
    img_upload = FileField('Upload Figure (new)', [FileAllowed(list(config.forms.ALLOWED_EXTENSIONS), 'File type is not valid.')])
    img_delete = BooleanField('Delete Figure')

    caption_validators = [validators.Length(max=600)]
    if config.submission.require_figure_caption:
        caption_validators.append(validator_img())
    img_caption = TextAreaField('Figure Caption', caption_validators)

    halt_on_error = BooleanField('Stop LaTeX on Error')

### Abstract Submission invited  ###

class Affiliation_invited(BaseForm):

    if config.institute_presets:
        institute = SelectField('Institute/University', [validator_deny_first_selection()], choices=config.forms.institute_choices)
        institute_alt = StringField('Institute/University', [validators.Length(max=100)])
    else:
        institute = StringField('Institute/University', [validators.Length(max=100)])

    department = StringField('Department', [validators.Length(max=100)])
    street = StringField('Street/Number', [validators.Length(max=100)])
    postal_code = StringField('Postal Code', [validators.Length(max=10)])
    city = StringField('City', [validators.Length(max=100)])
    country = SelectField('Country', choices=config.forms.country_choices, default=config.forms.default_country_id)

class Abstract_invited(BaseForm):

    btest = StringField('', [validators.AnyOf('')])    # Bot Protection

    authors = FieldList(FormField(Author))
    affiliations = FieldList(FormField(Affiliation_invited))

    category = SelectField('Category')
    title = StringField('Title', [validators.Length(max=300)])
    content = TextAreaField('Abstract')

    img_use = BooleanField('Include Figure')
    img_width = IntegerField('Width (1-100%)', [validators.NumberRange(min=1,max=100)])
    img_caption = TextAreaField('Figure Caption', [validators.Length(max=600)])
    img_upload = FileField('Upload Figure (new)', [FileAllowed(list(config.forms.ALLOWED_EXTENSIONS), 'File type is not valid.')])
    img_delete = BooleanField('Delete Figure')

    portrait_upload = FileField('Upload Portrait (new)', [FileAllowed(list(config.forms.ALLOWED_EXTENSIONS), 'File type is not valid.')])
    portrait_delete = BooleanField('Delete Figure')

    halt_on_error = BooleanField('Stop LaTeX on Error')
