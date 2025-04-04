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
from senaite.ast import utils
from zope.component import adapter
from zope.interface import implementer


@adapter(IListingView)
@implementer(IListingViewAdapter)
class AddAnalysesViewAdapter(object):
    """Adapter for services listing from Worksheet's Add Analyses view
    """

    # Priority order of this adapter over others
    priority_order = 50

    def __init__(self, listing, context):
        self.listing = listing
        self.context = context

    def before_render(self):
        # Do not display AST services
        pocs = utils.get_non_ast_points_of_capture()
        self.listing.contentFilter.update({
            "getPointOfCapture": pocs,
        })

    def folder_item(self, obj, item, index):  # noqa
        return item
