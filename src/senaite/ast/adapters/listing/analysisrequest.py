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
from plone.memoize import instance
from senaite.app.listing.interfaces import IListingView
from senaite.app.listing.interfaces import IListingViewAdapter
from senaite.ast.interfaces import IASTAnalysis
from senaite.core.catalog import SETUP_CATALOG
from zope.component import adapter
from zope.interface import implementer


@adapter(IListingView)
@implementer(IListingViewAdapter)
class ManageAnalysesViewAdapter(object):
    """Adapter for Manage Analyses (as services) from Sample view
    """

    # Priority order of this adapter over others
    priority_order = 50

    def __init__(self, listing, context):
        self.listing = listing
        self.context = context

    def before_render(self):
        # Do not display AST services
        pocs = self.get_non_ast_pocs()
        self.listing.contentFilter.update({
            "point_of_capture": pocs,
        })

        # Skip Sample's AST analyses
        is_ast = IASTAnalysis.providedBy
        analyses = self.listing.analyses.items()
        analyses = filter(lambda an: not is_ast(an[1]), analyses)
        self.listing.analyses = dict(analyses)

    @instance.memoize
    def get_non_ast_pocs(self):
        """Return the available points of capture from services that are not ast
        """
        catalog = api.get_tool(SETUP_CATALOG)
        pocs = catalog.Indexes["point_of_capture"].uniqueValues()
        pocs = filter(lambda poc: poc != "ast", pocs)
        return pocs

    def folder_item(self, obj, item, index):  # noqa
        return item
