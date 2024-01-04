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

from bika.lims import api
from bika.lims.utils import get_link
from senaite.app.listing.interfaces import IListingView
from senaite.app.listing.interfaces import IListingViewAdapter
from senaite.app.listing.utils import add_column
from senaite.ast import check_installed
from senaite.ast import messageFactory as _
from zope.component import adapter
from zope.interface import implementer

# Columns to add
ADD_COLUMNS = [
    ("Extrapolated", {
        "title": _("Extrapolated antibiotics"),
        "toggle": True,
        "after": "Description",
    }),
]


@implementer(IListingViewAdapter)
@adapter(IListingView)
class AntibioticsListingViewAdapter(object):
    """Adapter for Antibiotics listing
    """

    # Priority order of this adapter over others
    priority_order = 99999

    def __init__(self, listing, context):
        self.listing = listing
        self.context = context

    @check_installed(None)
    def folder_item(self, obj, item, index):
        obj = api.get_object(obj)
        extrapolated_uids = obj.extrapolated_antibiotics or []
        extrapolated_links = map(self.get_link, extrapolated_uids)
        item["Extrapolated"] = extrapolated_uids
        item["replace"]["Extrapolated"] = ", ".join(extrapolated_links)

    def get_link(self, antibiotic_uid):
        obj = api.get_object(antibiotic_uid)
        url = api.get_url(obj)
        title = api.get_title(obj)
        abbr = obj.abbreviation
        if abbr:
            title = "{} ({})".format(title, abbr)
        return get_link(href=url, value=title)

    @check_installed(None)
    def before_render(self):
        # Additional columns
        rv_keys = map(lambda r: r["id"], self.listing.review_states)
        for column_id, column_values in ADD_COLUMNS:
            add_column(
                listing=self.listing,
                column_id=column_id,
                column_values=column_values,
                after=column_values.get("after", None),
                review_states=rv_keys)
