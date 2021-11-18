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
        title=_("Antibiotic"),
        source="senaite.ast.vocabularies.antibiotics",
        required=True,
    )

    microorganism = schema.Choice(
        title=_(u"Species"),
        source="senaite.ast.vocabularies.species",
        required=True,
    )

    disk_content = schema.Int(
        title=_(u"Disk content (μg)"),
        min=0,
        required=True,
    )

    diameter_s = schema.Int(
        title=_(u"S ≥ (mm)"),
        description=_(u"Susceptible"),
        min=0,
        required=True,
    )

    diameter_r = schema.Int(
        title=_(u"R < (mm)"),
        description=_(u"Resistant"),
        min=0,
        required=True,
    )


@provider(IFormFieldProvider)
class IBreakpointsTableBehavior(model.Schema):

    breakpoints = DataGridField(
        title=_(u"Clinical Breakpoints"),
        description=_(
            u"List of susceptibility testing categories breakpoints for this "
            u"antimicrobial agent depending on the concentration added to the "
            u"filter paper (disk content or potency) expressed in μg and the "
            u"microorganism to test. These zone diameter breakpoints are used "
            u"on AST results entry view to automatically calculate the "
            u"susceptibility testing category."
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

    def _get_breakpoints(self):
        return self.context.breakpoints

    def _set_breakpoints(self, value):
        self.context.breakpoints = value

    breakpoints = property(_get_breakpoints, _set_breakpoints)
