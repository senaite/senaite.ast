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
# Copyright 2020-2024 by it's authors.
# Some rights reserved, see README and LICENSE.

from plone.autoform.interfaces import IFormFieldProvider
from plone.dexterity.utils import getAdditionalSchemata
from plone.supermodel import model
from senaite.abx.interfaces import IAntibiotic
from senaite.ast import messageFactory as _
from zope import schema
from zope.component import adapter
from zope.interface import implementer
from zope.interface import provider


@provider(IFormFieldProvider)
class IExtrapolatedAntibioticsBehavior(model.Schema):

    extrapolated_antibiotics = schema.List(
        title=_(u"Extrapolated antibiotics"),
        description=_(
            "The sensitivity results obtained for this particular antibiotic "
            "will be extrapolated to these other antibiotics and will "
            "therefore be displayed in results reports too"
        ),
        value_type=schema.Choice(
            source="senaite.ast.vocabularies.antibiotics"
        )
    )


@implementer(IExtrapolatedAntibioticsBehavior)
@adapter(IAntibiotic)
class ExtendedAntibiotic(object):

    def __init__(self, context):
        self.context = context
        self._schema = None

    @property
    def schema(self):
        """Return the schema provided by the underlying behavior
        """
        if self._schema is None:
            schemata = getAdditionalSchemata(context=self.context)
            for sch in schemata:
                if sch.isOrExtends(IExtrapolatedAntibioticsBehavior):
                    self._schema = sch
                    return self._schema
            raise TypeError("Not a valid context")
        return self._schema

    def accessor(self, fieldname):
        """Return the field accessor for the fieldname
        """
        if fieldname in self.schema:
            return self.schema[fieldname].get
        return None

    def mutator(self, fieldname):
        """Return the field mutator for the fieldname
        """
        if fieldname in self.schema:
            return self.schema[fieldname].set
        return None

    def getExtrapolatedAntibiotics(self):
        accessor = self.accessor("extrapolated_antibiotics")
        return accessor(self.context)

    def setExtrapolatedAntibiotics(self, value):
        mutator = self.mutator("extrapolated_antibiotics")
        mutator(self.context, value)

    extrapolated_antibiotics = property(getExtrapolatedAntibiotics,
                                        setExtrapolatedAntibiotics)
