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

import collections

from bika.lims import _ as _c
from bika.lims.catalog import SETUP_CATALOG
from bika.lims.utils import get_link
from bika.lims.utils import get_link_for
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from senaite.app.listing import ListingView
from senaite.ast import messageFactory as _
from bika.lims import api
from plone.memoize import view
from senaite.ast.browser.duplicateview import DuplicateView


class ASTPanelFolderView(ListingView):
    """AST Panels listing view
    """

    def __init__(self, context, request):
        super(ASTPanelFolderView, self).__init__(context, request)

        self.catalog = SETUP_CATALOG

        self.contentFilter = {
            "portal_type": "ASTPanel",
            "sort_on": "sortable_title",
            "sort_order": "ascending",
        }

        self.context_actions = {
            _c("Add"): {
                "url": "++add++ASTPanel",
                "icon": "add.png"}
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
            ("Microorganisms", {
                "title": _("Microorganisms"),
            }),
            ("Antibiotics", {
                "title": _("Antibiotics"),
            })
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
        super(ASTPanelFolderView, self).update()

    def before_render(self):
        """Before template render hook
        """
        super(ASTPanelFolderView, self).before_render()

    def folderitem(self, obj, item, index):
        """Service triggered each time an item is iterated in folderitems.
        The use of this service prevents the extra-loops in child objects.
        :obj: the instance of the class to be foldered
        :item: dict containing the properties of the object to be used by
            the template
        :index: current index of the item
        """
        item["replace"]["Title"] = get_link_for(obj)

        obj = api.get_object(obj)

        # Antibiotic links
        antibiotics = map(self.get_antibiotic_info, obj.antibiotics)
        links = map(lambda a: a.get("link"), antibiotics)
        item["replace"]["Antibiotics"] = ", ".join(links)

        # Microorganism links
        microorganisms = map(self.get_microorganism_info, obj.microorganisms)
        links = map(lambda m: m.get("link"), microorganisms)
        item["replace"]["Microorganisms"] = ", ".join(links)

        return item

    def get_children_hook(self, parent_uid, child_uids=None):
        """Hook to get the children of an item
        """
        super(ASTPanelFolderView, self).get_children_hook(
            parent_uid, child_uids=child_uids)

    @view.memoize
    def get_antibiotic_info(self, uid_brain_object):
        uid = api.get_uid(uid_brain_object)
        obj = api.get_object(uid_brain_object)

        href = api.get_url(obj)
        title = api.get_title(obj)
        abbreviation = obj.abbreviation or title

        return {
            "uid": uid,
            "link": get_link(href=href, value=abbreviation, title=title),
            "abbreviation": abbreviation,
            "title": title,
        }

    @view.memoize
    def get_microorganism_info(self, uid_brain_object):
        uid = api.get_uid(uid_brain_object)
        obj = api.get_object(uid_brain_object)
        title = api.get_title(obj)
        params = {
            "href": api.get_url(obj),
            "value": title,
        }
        if obj.multi_resistant:
            params.update({
                "value": "{}*".format(title),
                "title": _("Multi-resistant (MRO)")
            })

        return {
            "uid": uid,
            "link": get_link(**params),
            "title": title,
        }


class ASTPanelsDuplicate(DuplicateView):
    template = ViewPageTemplateFile("templates/astpaneltables_duplicate.pt")

    def __call__(self):
        return super(ASTPanelsDuplicate, self).__call__()
