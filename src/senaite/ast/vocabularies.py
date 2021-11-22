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

from bika.lims import api
from bika.lims.catalog import SETUP_CATALOG
from senaite.ast import messageFactory as _
from zope.interface import implementer
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary


def to_simple_term(obj, prefix=""):
    uid = api.get_uid(obj)
    title = "{}{}".format(prefix, api.get_title(obj))
    return SimpleTerm(uid, title=title)


def to_simple_vocabulary(query, catalog_id):
    brains = api.search(query, catalog_id)
    items = map(to_simple_term, brains)
    return SimpleVocabulary(items)


@implementer(IVocabularyFactory)
class AntibioticsVocabulary(object):

    def __call__(self, context):
        query = {
            "portal_type": "Antibiotic",
            "is_active": True,
            "sort_on": "sortable_title",
            "sort_order": "ascending",
        }
        return to_simple_vocabulary(query, SETUP_CATALOG)


@implementer(IVocabularyFactory)
class MicroorganismsVocabulary(object):

    def __call__(self, context):
        query = {
            "portal_type": "Microorganism",
            "is_active": True,
            "sort_on": "sortable_title",
            "sort_order": "ascending",
        }
        return to_simple_vocabulary(query, SETUP_CATALOG)


@implementer(IVocabularyFactory)
class SpeciesVocabulary(object):
    """Returns a SimpleVocabulary made of MicroorganismCategory and
    Microorganism objects, grouped
    """

    _microorganisms = None

    def __call__(self, context):
        items = []
        query = {
            "portal_type": ["MicroorganismCategory"],
            "is_active": True,
            "sort_on": "sortable_title",
            "sort_order": "ascending",
        }
        for category in api.search(query, SETUP_CATALOG):
            cat_uid = api.get_uid(category)
            title = api.get_title(category).upper()
            items.append(SimpleTerm(cat_uid, title=title))

            # Append the microorganisms for this category
            microorganisms = self.microorganisms_grouped.get(cat_uid, [])
            for microorganism in microorganisms:
                term = to_simple_term(microorganism, prefix="-- ")
                items.append(term)

        # Append the microorganisms not yet categorized at the end
        microorganisms = self.microorganisms_grouped.get(None, [])
        if microorganisms:
            # Add a "Not categorized" group
            term = SimpleTerm("", title=_("Uncategorized").upper())
            items.append(term)

            for microorganism in microorganisms:
                term = to_simple_term(microorganism, prefix="-- ")
                items.append(term)

        return SimpleVocabulary(items)

    @property
    def microorganisms_grouped(self):
        if self._microorganisms is None:
            self._microorganisms = {}
            query = {
                "portal_type": ["Microorganism"],
                "is_active": True,
                "sort_on": "sortable_title",
                "sort_order": "ascending",
            }
            brains = api.search(query, SETUP_CATALOG)
            for brain in brains:
                obj = api.get_object(brain)
                cat_uid = obj.category and obj.category[0] or None
                self._microorganisms.setdefault(cat_uid, []).append(brain)

        return self._microorganisms


AntibioticsVocabularyFactory = AntibioticsVocabulary()
MicroorganismsVocabularyFactory = MicroorganismsVocabulary()
SpeciesVocabularyFactory = SpeciesVocabulary()
