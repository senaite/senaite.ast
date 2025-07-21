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

from senaite.app.listing.interfaces import IListingView
from senaite.app.listing.interfaces import IListingViewAdapter
from senaite.ast.config import IDENTIFICATION_KEY
from zope.component import adapter
from zope.interface import implementer

@implementer(IListingViewAdapter)
@adapter(IListingView)
class AnalysesViewAdapter(object):
    """Adapter for analyses listing
    """

    def __init__(self, listing, context):
        self.listing = listing
        self.context = context

    def folder_item(self, obj, item, index):
        keyword = obj.getKeyword
        if keyword == IDENTIFICATION_KEY:
            # reload the current view on analysis submit to make the section
            # for the selection of AST panels to become visible and properly
            # populated with panels that include at least one of the selected
            # microorganisms
            item["reload"] = ["submit"]

    def before_render(self):
        pass
