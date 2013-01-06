#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    openslides.motion.models
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Models for the motion app.

    :copyright: 2011, 2012 by OpenSlides team, see AUTHORS.
    :license: GNU GPL, see LICENSE for more details.
"""

from datetime import datetime

from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import Max
from django.dispatch import receiver
from django.utils.translation import pgettext
from django.utils.translation import ugettext_lazy as _, ugettext_noop, ugettext

from openslides.utils.utils import _propper_unicode
from openslides.utils.person import PersonField
from openslides.config.models import config
from openslides.config.signals import default_config_value
from openslides.poll.models import (
    BaseOption, BasePoll, CountVotesCast, CountInvalid, BaseVote)
from openslides.participant.models import User
from openslides.projector.api import register_slidemodel
from openslides.projector.models import SlideMixin
from openslides.agenda.models import Item


RELATION = (
    (1, _('Submitter')),
    (2, _('Supporter')))


class RelatedPersonsManager(models.Manager):
    def __init__(self, relation, *args, **kwargs):
        super(RelatedPersonsManager, self).__init__(*args, **kwargs)
        for key, value in RELATION:
            if key == relation:
                self.relation = key
                break
        else:
            raise ValueError('Unknown relation with id %d' % relation)

    def get_query_set(self):
        return (super(RelatedPersonsManager, self).get_query_set()
                .filter(relation=self.relation))


class MotionRelatedPersons(models.Model):
    submitter = RelatedPersonsManager(relation=1)
    supporter = RelatedPersonsManager(relation=2)
    objects = models.Manager()

    person = PersonField()
    relation = models.IntegerField(default=1, choices=RELATION)
    motion = models.ForeignKey('Motion', related_name="persons")


class Motion(SlideMixin, models.Model):
    prefix = "motion"  # Rename this in the slide-system

    # TODO: Use this attribute for the default_version, if the permission system
    #       is deactivated. Maybe it has to be renamed.
    permitted_version = models.ForeignKey(
        'MotionVersion', null=True, blank=True, related_name="permitted")
    # TODO: Define status
    status = models.CharField(max_length=3)
    # Log (Translatable)
    identifier = models.CharField(max_length=255, null=True, blank=True,
                                  unique=True)
    category = models.ForeignKey('Category', null=True, blank=True)
    # TODO proposal
    # Maybe rename to master_copy
    master = models.ForeignKey('self', null=True, blank=True)

    class Meta:
        permissions = (
            ('can_see_motion', ugettext_noop('Can see motions')),
            ('can_create_motion', ugettext_noop('Can create motions')),
            ('can_support_motion', ugettext_noop('Can support motions')),
            ('can_manage_motion', ugettext_noop('Can manage motions')),
        )
        # TODO: order per default by category and identifier
        # ordering = ('number',)

    def __unicode__(self):
        return self.get_title()

    # TODO: Use transaction
    def save(self, *args, **kwargs):
        super(Motion, self).save(*args, **kwargs)
        new_data = False
        for attr in ['_title', '_text', '_reason']:
            if hasattr(self, attr):
                new_data = True
                break
        need_new_version = True #  TODO: Do we need a new version (look in config)
        if hasattr(self, '_version') or (new_data and need_new_version):
            version = self.new_version
            del self._new_version
            version.motion = self  # Test if this line is realy neccessary.
        elif new_data and not need_new_version:
            # TODO: choose an explicit version
            version = self.last_version
        else:
            # We do not need to save the motion version
            return
        for attr in ['title', 'text', 'reason']:
            _attr = '_%s' % attr
            try:
                setattr(version, attr, getattr(self, _attr))
            except AttributeError:
                setattr(version, attr, getattr(self.last_version, attr))
        version.save()

    def get_absolute_url(self, link='detail'):
        if link == 'view' or link == 'detail':
            return reverse('motion_detail', args=[str(self.id)])
        if link == 'edit':
            return reverse('motion_edit', args=[str(self.id)])
        if link == 'delete':
            return reverse('motion_delete', args=[str(self.id)])

    def get_title(self):
        try:
            return self._title
        except AttributeError:
            return self.default_version.title

    def set_title(self, title):
        self._title = title

    title = property(get_title, set_title)

    def get_text(self):
        try:
            return self._text
        except AttributeError:
            return self.default_version.text

    def set_text(self, text):
        self._text = text

    text = property(get_text, set_text)

    def get_reason(self):
        try:
            return self._reason
        except AttributeError:
            return self.default_version.reason

    def set_reason(self, reason):
        self._reason = reason

    reason = property(get_reason, set_reason)

    @property
    def new_version(self):
        try:
            return self._new_version
        except AttributeError:
            self._new_version = MotionVersion(motion=self)
            return self._new_version

    @property
    def submitter(self):
        return MotionRelatedPersons.submitter.filter(motion=self)

    @property
    def supporter(self):
        return MotionRelatedPersons.supporter.filter(motion=self)

    def get_version(self, version_id):
        # TODO: Check case, if version_id is not one of this motion
        return self.versions.get(pk=version_id)


    def get_default_version(self):
        try:
            return self._default_version
        except AttributeError:
            # TODO: choose right version via config
            return self.last_version

    def set_default_version(self, version):
        if version is None:
            try:
                del self._default_version
            except AttributeError:
                pass
        else:
            if type(version) is int:
                version = self.versions.all()[version]
            elif type(version) is not MotionVersion:
                raise ValueError('The argument \'version\' has to be int or '
                                 'MotionVersion, not %s' % type(version))
            self._default_version = version

    default_version = property(get_default_version, set_default_version)

    @property
    def last_version(self):
        # TODO: Fix the case, that the motion has no Version
        try:
            return self.versions.order_by('id').reverse()[0]
        except IndexError:
            return self.new_version


class MotionVersion(models.Model):
    title = models.CharField(max_length=255, verbose_name=_("Title"))
    text = models.TextField(verbose_name=_("Text"))
    reason = models.TextField(null=True, blank=True, verbose_name=_("Reason"))
    rejected = models.BooleanField(default=False)
    creation_time = models.DateTimeField(auto_now=True)
    motion = models.ForeignKey(Motion, related_name='versions')
    identifier = models.CharField(max_length=255, verbose_name=_("Version identifier"))
    note = models.TextField(null=True, blank=True)

    def __unicode__(self):
        return "%s Version %s" % (self.motion, self.get_version_number())

    def get_version_number(self):
        if self.pk is None:
            return 'new'
        return (MotionVersion.objects.filter(motion=self.motion)
                                     .filter(id__lte=self.pk).count())


class Category(models.Model):
    name = models.CharField(max_length=255, verbose_name=_("Category name"))
    prefix = models.CharField(max_length=32, verbose_name=_("Category prefix"))

    def __unicode__(self):
        return self.name


class Comment(models.Model):
    motion_version = models.ForeignKey(MotionVersion)
    text = models.TextField()
    author = PersonField()
    creation_time = models.DateTimeField(auto_now=True)
