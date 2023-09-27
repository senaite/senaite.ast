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
# Copyright 2020-2022 by it's authors.
# Some rights reserved, see README and LICENSE.

from copy import copy

from bika.lims import api
from plone.autoform import directives
from plone.autoform.interfaces import IFormFieldProvider
from plone.behavior.interfaces import IBehavior
from plone.dexterity.interfaces import IDexterityContent
from plone.supermodel import model
from senaite.ast import messageFactory as _
from senaite.core.catalog import SETUP_CATALOG
from senaite.core.schema import UIDReferenceField
from senaite.core.z3cform.widgets.uidreference import UIDReferenceWidgetFactory
from zope import schema
from zope.component import adapter
from zope.interface import implementer
from zope.interface import provider


@provider(IFormFieldProvider)
class IASTPanelBehavior(model.Schema):

    microorganisms = schema.List(
        title=_(u"Microorganisms"),
        description=_(
            u"The names of selected microorganisms are displayed as row "
            u"headers in the sensitivity results entry view. From all "
            u"microorganisms selected here, only those identified in the "
            u"Sample are added in results entry view"
        ),
        required=True,
        value_type=schema.Choice(
            source="senaite.ast.vocabularies.microorganisms"
        )
    )

    antibiotics = schema.List(
        title=_(u"Antibiotics"),
        description=_(
            u"The abbreviations of selected antibiotics are displayed as "
            u"column headers in the sensitivity results entry view"
        ),
        required=True,
        value_type=schema.Choice(
            source="senaite.ast.vocabularies.antibiotics"
        )
    )

    breakpoints_table = UIDReferenceField(
        title=_(u"Clinical breakpoints table"),
        description=_(
            u"Default clinical breakpoints table to use for this panel. If "
            u"set, the system will automatically calculate the susceptibility "
            u"testing category as soon as the zone diameter in mm is submitted "
            u"by the user."
        ),
        allowed_types=("BreakpointsTable", ),
        multi_valued=False,
        required=False,
    )

    directives.widget(
        "breakpoints_table",
        UIDReferenceWidgetFactory,
        catalog=SETUP_CATALOG,
        query={
            "portal_type": "BreakpointsTable",
            "is_active": True,
            "sort_on": "title",
            "sort_order": "ascending",
        },
        display_template="<a href='${url}'>${title}</a>",
        columns=[
            {
                "name": "title",
                "width": "30",
                "align": "left",
                "label": _(u"Title"),
            }, {
                "name": "description",
                "width": "70",
                "align": "left",
                "label": _(u"Description"),
            },
        ],
        limit=15,
    )

    method = schema.Choice(
        title=_(u"label_astpanel_method", default=u"Method"),
        description=_(
            u"description_astpanel_method",
            default=u"The method to determine microbial susceptibility to "
                    u"antibiotics"
        ),
        source="senaite.ast.vocabularies.ast_methods",
        required=True,
        default="diffusion_disk",
    )

    disk_content = schema.Bool(
        title=_(u"Include disk content in μg"),
        description=_(
            u"When enabled, an additional row for the introduction of the disk "
            u"content (potency) in μg is displayed in the results entry view, "
            u"above resistance call options"
        ),
        required=False,
        default=False,
    )

    zone_size = schema.Bool(
        title=_(
            u"title_astpanel_zone_size",
            default=u"Include zone diameter in mm"
        ),
        description=_(
            u"description_astpanel_zone_size",
            default=u"When enabled, an additional row for the introduction of "
                    u"the diameter of inhibition zone (DIZ) in mm is "
                    u"displayed in the results entry view, above resistance "
                    u"call options."
        ),
        required=False,
        default=True,
    )

    mic_value = schema.Bool(
        title=_(
            u"title_astpanel_mic_value",
            default=u"Include MIC value in μg/mL"
        ),
        description=_(
            u"description_astpanel_mic_value",
            default=u"When enabled, an additional row for the introduction of "
                    u"the Minimum Inhibitory Concentration value in μg/mL is "
                    u"displayed in the results entry view, above resistance "
                    u"call options."
        ),
        required=False,
        default=True,
    )

    selective_reporting = schema.Bool(
        title=_(u"Selective reporting"),
        description=_(
            u"When enabled, an additional row to indicate whether the "
            u"resistance result for each microorganism-antibiotic tuple has to "
            u"be reported in results report or not"
        ),
        required=False,
        default=False,
    )


@implementer(IBehavior, IASTPanelBehavior)
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

    def _set_breakpoints_table(self, value):
        self.context.breakpoints_table = value

    def _get_breakpoints_table(self):
        breakpoints_table = getattr(self.context, "breakpoints_table", None)
        return copy(breakpoints_table)

    breakpoints_table = property(_get_breakpoints_table, _set_breakpoints_table)

    def _set_disk_content(self, value):
        self.context.disk_content = value

    def _get_disk_content(self):
        disk_content = getattr(self.context, "disk_content", None)
        return disk_content

    disk_content = property(_get_disk_content, _set_disk_content)

    def _set_zone_size(self, value):
        self.context.zone_size = value

    def _get_zone_size(self):
        zone_size = getattr(self.context, "zone_size", None)
        return zone_size

    zone_size = property(_get_zone_size, _set_zone_size)

    def _set_selective_reporting(self, value):
        self.context.selective_reporting = value

    def _get_selective_reporting(self):
        selective_reporting = getattr(self.context, "selective_reporting", None)
        return selective_reporting

    selective_reporting = property(_get_selective_reporting, _set_selective_reporting)

    def _set_method(self, value):
        self.context.method = value

    def _get_method(self):
        return getattr(self.context, "method")

    method = property(_get_method, _set_method)

    def _set_mic_value(self, value):
        self.context.method = value

    def _get_mic_value(self):
        return getattr(self.context, "method")

    mic_value = property(_get_mic_value, _set_mic_value)
