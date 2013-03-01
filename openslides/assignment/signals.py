#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    openslides.assignment.signals
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Signals for the assignment app.

    :copyright: (c) 2011–2013 by the OpenSlides team, see AUTHORS.
    :license: GNU GPL, see LICENSE for more details.
"""

from django.dispatch import receiver
from django import forms
from django.utils.translation import ugettext_lazy, ugettext_noop, ugettext as _

from openslides.config.signals import config_signal
from openslides.config.api import ConfigVariable, ConfigPage


@receiver(config_signal, dispatch_uid='setup_assignment_config_page')
def setup_assignment_config_page(sender, **kwargs):
    """
    Assignment config variables.
    """
    assignment_publish_winner_results_only = ConfigVariable(
        name='assignment_publish_winner_results_only',
        default_value=False,
        form_field=forms.BooleanField(
            required=False,
            label=_('Only publish voting results for selected winners '
                    '(Projector view only)')))
    assignment_pdf_ballot_papers_selection = ConfigVariable(
        name='assignment_pdf_ballot_papers_selection',
        default_value='CUSTOM_NUMBER',
        form_field=forms.ChoiceField(
            widget=forms.Select(),
            required=False,
            label=_('Number of ballot papers (selection)'),
            choices=(
                ('NUMBER_OF_DELEGATES', _('Number of all delegates')),
                ('NUMBER_OF_ALL_PARTICIPANTS', _('Number of all participants')),
                ('CUSTOM_NUMBER', _('Use the following custom number')))))
    assignment_pdf_ballot_papers_number = ConfigVariable(
        name='assignment_pdf_ballot_papers_number',
        default_value=8,
        form_field=forms.IntegerField(
            widget=forms.TextInput(attrs={'class': 'small-input'}),
            required=False,
            min_value=1,
            label=_('Custom number of ballot papers')))
    assignment_pdf_title = ConfigVariable(
        name='assignment_pdf_title',
        default_value=_('Elections'),
        form_field=forms.CharField(
            widget=forms.TextInput(),
            required=False,
            label=_('Title for PDF document (all elections)')))
    assignment_pdf_preamble = ConfigVariable(
        name='assignment_pdf_preamble',
        default_value='',
        form_field=forms.CharField(
            widget=forms.Textarea(),
            required=False,
            label=_('Preamble text for PDF document (all elections)')))
    assignment_poll_vote_values = ConfigVariable(
        name='assignment_poll_vote_values',
        default_value='auto',
        form_field=forms.ChoiceField(
            widget=forms.Select(),
            required=False,
            label=_('Election method'),
            choices=(
                ('auto', _('Automatic assign of method.')),
                ('votes', _('Always one option per candidate.')),
                ('yesnoabstain', _('Always Yes-No-Abstain per candidate.')))))

    return ConfigPage(title=ugettext_noop('Elections'),
                      url='assignment',
                      required_permission='config.can_manage',
                      weight=40,
                      variables=(assignment_publish_winner_results_only,
                                 assignment_pdf_ballot_papers_selection,
                                 assignment_pdf_ballot_papers_number,
                                 assignment_pdf_title,
                                 assignment_pdf_preamble,
                                 assignment_poll_vote_values))
