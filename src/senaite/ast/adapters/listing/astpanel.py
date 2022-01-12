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
from senaite.app.listing.interfaces import IListingView
from senaite.app.listing.interfaces import IListingViewAdapter
from senaite.ast import messageFactory as _
from senaite.ast import utils
from zope.component import adapts
from zope.interface import implements


class ASTPanelViewAdapter(object):
    """Adapter for ASTPanel view from Sample context
    """
    adapts(IListingView)
    implements(IListingViewAdapter)

    # Priority order of this adapter over others
    priority_order = 99999

    def __init__(self, listing, context):
        self.listing = listing
        self.context = context

    def before_render(self):
        # If there are microorganisms identified for the current sample,
        # display a new filter "Identified microorganisms" and make it the
        # default, so only identified microorganisms are listed
        microorganisms = utils.get_identified_microorganisms(self.context)
        if microorganisms:
            # Get the microorganisms uids
            uids = map(api.get_uid, microorganisms)

            # Make the original review state not default's
            self.listing.review_states[0].update({
                "id": "all"
            })

            # Insert the new "default" review state
            self.listing.review_states.insert(0, {
                "id": "default",
                "title": _("Identified microorganisms"),
                "contentFilter": {"UID": uids},
                "columns": self.listing.columns.keys()
            })

    def folder_item(self, obj, item, index):  # noqa
        return item
