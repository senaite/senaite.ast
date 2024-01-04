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

import collections

from bika.lims import _ as _c
from bika.lims import api
from bika.lims.catalog import SETUP_CATALOG
from bika.lims.utils import get_link_for
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from senaite.app.listing import ListingView
from senaite.ast.browser.duplicateview import DuplicateView


class BreakpointsTablesView(ListingView):
    """Breakpoints tables listing view
    """

    def __init__(self, context, request):
        super(BreakpointsTablesView, self).__init__(context, request)

        self.catalog = SETUP_CATALOG

        self.contentFilter = {
            "portal_type": "BreakpointsTable",
            "sort_on": "sortable_title",
            "sort_order": "ascending",
        }

        self.context_actions = {
            _c("Add"): {
                "url": "++add++BreakpointsTable",
                "icon": "add.png"
            }
        }

        self.show_select_column = True

        self.columns = collections.OrderedDict((
            ("Title", {
                "title": _c("Title"),
                "index": "sortable_title"
            }),
            ("Description", {
                "title": _c("Description"),
                "index": "Description"
            }),
        ))

        copy_transition = {
            "id": "duplicate",
            "title": _c("Duplicate"),
            "url": "{}/copy".format(api.get_url(self.context))
        }

        self.review_states = [
            {
                "id": "default",
                "title": _c("Active"),
                "contentFilter": {"is_active": True},
                "transitions": [],
                "columns": self.columns.keys(),
                "custom_transitions": [copy_transition]
            }, {
                "id": "inactive",
                "title": _c("Inactive"),
                "contentFilter": {'is_active': False},
                "transitions": [],
                "columns": self.columns.keys(),
                "custom_transitions": [copy_transition]
            }, {
                "id": "all",
                "title": _c("All"),
                "contentFilter": {},
                "columns": self.columns.keys(),
                "custom_transitions": [copy_transition]
            },
        ]

    def update(self):
        """Update hook
        """
        super(BreakpointsTablesView, self).update()

    def before_render(self):
        """Before template render hook
        """
        super(BreakpointsTablesView, self).before_render()

    def folderitem(self, obj, item, index):
        """Service triggered each time an item is iterated in folderitems.
        The use of this service prevents the extra-loops in child objects.
        :obj: the instance of the class to be foldered
        :item: dict containing the properties of the object to be used by
            the template
        :index: current index of the item
        """
        item["replace"]["Title"] = get_link_for(obj)
        return item


class ASTBreakpointsTablesDuplicate(DuplicateView):
    template = ViewPageTemplateFile("templates/breakpointstables_duplicate.pt")

    def __call__(self):
        return super(ASTBreakpointsTablesDuplicate, self).__call__()
