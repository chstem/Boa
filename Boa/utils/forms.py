# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from ..modules import config, database, forms
from .contributions import get_contribution_choices

def create_abstract_form(participant):
    """Create abstract submission form."""

    if participant.rank in config.registration.ranks_invited:
        form = forms.Abstract_invited()
    else:
        form = forms.Abstract()
        form.contribution.choices = get_contribution_choices(participant)
    form.category.choices = [('pls_choose', '(please choose)')]
    form.category.choices += [(str(key), cat) for key, cat in enumerate(config.categories[participant.rank])]

    return form

def populate_abstract_form(participant):
    """Create abtract submission form and populate from database."""

    if participant.abstract.category in config.categories[participant.rank]:
        category = str(config.categories[participant.rank].index(participant.abstract.category))
    else:
        category = 'pls_choose'

    # remove '\\' from content
    content = participant.abstract.content

    if participant.rank in config.registration.ranks_invited:
        AbstractForm = forms.Abstract_invited
        AffiliationForm = forms.Affiliation_invited
    else:
        AbstractForm = forms.Abstract
        AffiliationForm = forms.Affiliation

    form = AbstractForm(
        contribution = 'None',
        title = participant.abstract.title,
        content = content,
        img_use = participant.abstract.img_use,
        img_width = participant.abstract.img_width,
        img_caption = participant.abstract.img_caption,
        halt_on_error = participant.halt_latex_on_error,
        )

    # add ListFields for authors and affiliations
    for author in participant.abstract.get_authors():
        subform = forms.Author()
        subform.firstname = author.firstname
        subform.lastname = author.lastname
        subform.affiliations = ', '.join(author.affiliation_keys)
        form.authors.append_entry(subform)

    for affil in participant.abstract.get_affiliations():

        subform = AffiliationForm()

        if config.institute_presets:
            if not affil.institute:
                subform.institute = 'pls_choose'
                subform.institute_alt = ''
            elif affil.institute in [institute[0] for institute in config.institute_presets]:
                subform.institute = [str(key) for key, institute in config.forms.institute_choices if institute == affil.institute][0]
                subform.institute_alt = ''
            else:
                subform.institute = 'other'
                subform.institute_alt = affil.institute
        else:
            subform.institute = affil.institute

        subform.department = affil.department
        subform.street = affil.street
        subform.postal_code = affil.postal_code
        subform.city = affil.city

        if affil.country in config.countries:
            subform.country = [str(key) for key, country in config.forms.country_choices if country == affil.country][0]

        form.affiliations.append_entry(subform)

    if not participant.rank in config.registration.ranks_invited:
        form.contribution.choices = get_contribution_choices(participant)
        form.contribution.data = participant.contribution

    # set rank specific categories
    form.category.choices = [('pls_choose', '(please choose)')] + [(str(key), cat) for key, cat in enumerate(config.categories[participant.rank])]
    form.category.data = category

    return form
