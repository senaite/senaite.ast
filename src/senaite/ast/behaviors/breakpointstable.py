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
# Copyright 2020-2025 by it's authors.
# Some rights reserved, see README and LICENSE.

from plone.autoform import directives
from plone.autoform.interfaces import IFormFieldProvider
from plone.dexterity.interfaces import IDexterityContent
from plone.supermodel import model
from senaite.ast import messageFactory as _
from senaite.core.schema.fields import DataGridField
from senaite.core.schema.fields import DataGridRow
from senaite.core.z3cform.widgets.datagrid import DataGridWidgetFactory
from zope import schema
from zope.component import adapter
from zope.interface import implementer
from zope.interface import Interface
from zope.interface import provider


class IBreakpointsTableSchema(Interface):

    antibiotic = schema.Choice(
        title=_(
            u"label_breakpoint_antibiotic",
            default=u"Antibiotic"
        ),
        source="senaite.ast.vocabularies.antibiotics",
        required=True,
    )

    microorganism = schema.Choice(
        title=_(
            u"label_breakpoint_microorganism",
            default=u"Species"
        ),
        source="senaite.ast.vocabularies.species",
        required=True,
    )

    mic_s = schema.Float(
        title=_(
            u"label_breakpoint_mic_s",
            default=u"S ≤ (μg/mL)"
        ),
        description=_(
            u"description_breakpoint_mic_s",
            default=u"MIC S (EUCAST: S ≤, CLSI: S ≤)",
        ),
        min=0.0,
        default=0.0,
        required=True,
    )

    mic_r = schema.Float(
        title=_(
            u"label_breakpoint_mic_r",
            default=u"R >/≥ (μg/mL)"
        ),
        description=_(
            u"description_breakpoint_mic_r",
            default=u"MIC R (EUCAST: R >, CLSI: R ≥)",
        ),
        min=0.0,
        default=0.0,
        required=True,
    )

    disk_content = schema.Int(
        title=_(
            u"label_breakpoint_disk_content",
            default=u"Disk content (μg)"
        ),
        min=0,
        required=True,
    )

    diameter_s = schema.Int(
        title=_(
            u"label_breakpoint_diameter_s",
            default=u"S ≥ (mm)"
        ),
        description=_(
            u"description_breakpoint_diameter_s",
            default=u"Zone diameter S (EUCAST: S ≥, CLSI: S ≥)",
        ),
        min=0,
        default=0,
        required=True,
    )

    diameter_r = schema.Int(
        title=_(
            u"label_breakpoint_diameter_r",
            default=u"R <≤ (mm)"
        ),
        description=_(
            u"description_breakpoint_diameter_r",
            default=u"Zone diameter R (EUCAST: R <, CLSI: R ≤)",
        ),
        min=0,
        default=0,
        required=True,
    )


@provider(IFormFieldProvider)
class IBreakpointsTableBehavior(model.Schema):

    guideline = schema.Choice(
        title=_(
            u"label_breakpointstable_guideline",
            default=u"Guideline"
        ),
        description=_(
            u"description_breakpointstable_guideline",
            default=u"Clinical guideline standard for interpretation boundaries "
                    u"applied to all breakpoints in this table"
        ),
        values=["EUCAST", "CLSI"],
        default="EUCAST",
        required=True,
    )

    breakpoints = DataGridField(
        title=_(
            u"label_breakpointstable",
            default=u"Clinical Breakpoints"
        ),
        description=_(
            u"description_breakpointstable",
            default=u"List of susceptibility testing categories breakpoints "
                    u"for this antimicrobial agent depending on the "
                    u"concentration added to the filter paper (disk content "
                    u"or potency) expressed in μg and the microorganism to "
                    u"test. These MIC and zone diameter breakpoints are used "
                    u"on AST results entry view to automatically calculate "
                    u"the susceptibility testing category."
        ),
        value_type=DataGridRow(
            title=u"Breakpoint",
            schema=IBreakpointsTableSchema),
        required=False,
        missing_value=[],
        default=[],
    )
    directives.widget(
        "breakpoints",
        DataGridWidgetFactory,
        auto_append=True)


@implementer(IBreakpointsTableBehavior)
@adapter(IDexterityContent)
class BreakpointsTable(object):

    def __init__(self, context):
        self.context = context

    def _get_guideline(self):
        return getattr(self.context, 'guideline', 'EUCAST')

    def _set_guideline(self, value):
        self.context.guideline = value

    guideline = property(_get_guideline, _set_guideline)

    def _get_breakpoints(self):
        return self.context.breakpoints

    def _set_breakpoints(self, value):
        self.context.breakpoints = value

    breakpoints = property(_get_breakpoints, _set_breakpoints)
