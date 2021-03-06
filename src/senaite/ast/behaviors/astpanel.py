# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.AST.
#
# SENAITE.AST is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Copyright 2020 by it's authors.
# Some rights reserved, see README and LICENSE.

from copy import copy

from bika.lims import api
from plone.autoform.interfaces import IFormFieldProvider
from plone.dexterity.interfaces import IDexterityContent
from plone.supermodel import model
from senaite.ast import messageFactory as _
from zope import schema
from zope.component import adapter
from zope.interface import implementer
from zope.interface import provider


@provider(IFormFieldProvider)
class IASTPanelBehavior(model.Schema):

    microorganisms = schema.List(
        title=_(u"Microorganisms"),
        description=_(
            "The names of selected microorganisms are displayed as row headers "
            "in the sensitivity results entry view. From all microorganisms "
            "selected here, only those identified in the Sample are added in "
            "results entry view"
        ),
        required=True,
        value_type=schema.Choice(
            source="senaite.ast.vocabularies.microorganisms"
        )
    )

    antibiotics = schema.List(
        title=_(u"Antibiotics"),
        description=_(
            "The abbreviations of selected antibiotics are displayed as "
            "column headers in the sensitivity results entry view"
        ),
        required=True,
        value_type=schema.Choice(
            source="senaite.ast.vocabularies.antibiotics"
        )
    )

    zone_size = schema.Bool(
        title=_(u"Include zone size in mm"),
        description=_(
            "When enabled, an additional row for the introduction of the zone "
            "size (in mm) is displayed in the results entry view, below "
            "resistance call options"
        ),
        default=True,
    )

    selective_reporting = schema.Bool(
        title=_(u"Selective reporting"),
        description=_(
            "When enabled, an additional row to indicate whether the "
            "resistance result for each microorganism-antibiotic tuple has to "
            "be reported in results report or not"
        ),
        default=True,
    )


@implementer(IASTPanelBehavior)
@adapter(IDexterityContent)
class ASTPanel(object):

    def __init__(self, context):
        self.context = context

    def to_uids(self, value):
        if not isinstance(value, (list, tuple)):
            value = [value]
        value = map(api.get_uid, value)
        return filter(None, value)

    def _set_microorganisms(self, value):
        self.context.microorganisms = self.to_uids(value)

    def _get_microorganisms(self):
        microorganisms = getattr(self.context, "microorganisms", []) or []
        return copy(microorganisms)

    microorganisms = property(_get_microorganisms, _set_microorganisms)

    def _set_antibiotics(self, value):
        self.context.antibiotics = self.to_uids(value)

    def _get_antibiotics(self):
        antibiotics = getattr(self.context, "antibiotics", []) or []
        return copy(antibiotics)

    antibiotics = property(_get_antibiotics, _set_antibiotics)
