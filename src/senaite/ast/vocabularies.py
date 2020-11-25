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
from zope.interface import implementer
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary


@implementer(IVocabularyFactory)
class AntibioticsVocabulary(object):

    def __call__(self, context):
        query = {
            "portal_type": "Antibiotic",
            "is_active": True,
            "sort_on": "sortable_title",
            "sort_order": "ascending",
        }
        brains = api.search(query, SETUP_CATALOG)
        items = [
            SimpleTerm(api.get_uid(brain), title=api.get_title(brain))
            for brain in brains
        ]
        return SimpleVocabulary(items)


@implementer(IVocabularyFactory)
class MicroorganismsVocabulary(object):

    def __call__(self, context):
        query = {
            "portal_type": "Microorganism",
            "is_active": True,
            "sort_on": "sortable_title",
            "sort_order": "ascending",
        }
        brains = api.search(query, SETUP_CATALOG)
        items = [
            SimpleTerm(api.get_uid(brain), title=api.get_title(brain))
            for brain in brains
        ]
        return SimpleVocabulary(items)


AntibioticsVocabularyFactory = AntibioticsVocabulary()
MicroorganismsVocabularyFactory = MicroorganismsVocabulary()
