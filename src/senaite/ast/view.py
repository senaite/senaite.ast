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
# Copyright 2020-2022 by it's authors.
# Some rights reserved, see README and LICENSE.

from bika.lims import _
from bika.lims import api
from bika.lims.catalog import SETUP_CATALOG
from Products.CMFPlone.utils import safe_unicode
from Products.Five import BrowserView
from transaction import savepoint


class DuplicateView(BrowserView):
    """Displays a list of object in a table to duplicate.
    """
    created = []

    def copy_object(self, source, title):
        """Creates a copy of the given object, but with the given title
        """
        # Validate the title
        portal_type = api.get_portal_type(api.get_object(source))
        err_msg = self.check_title(portal_type, title)

        if err_msg:
            self.context.plone_utils.addPortalMessage(
                safe_unicode(err_msg), "error")
            return

        # Create a copy
        return api.copy_object(source, title=title)

    def check_title(self, portal_type, title):
        """Checks if the given title is valid and unique. Returns an
        error message if not valid. None otherwise
        """
        if not title:
            return _("Validation failed: title is required")

        query = {"portal_type": portal_type, "Title": title}
        brains = api.search(query, SETUP_CATALOG)
        if brains:
            return _("Validation failed: title is already in use")
        return None

    def __call__(self):
        if "copy_form_submitted" not in self.request:
            uids = self.request.form.get("uids", [])
            self.objects = map(api.get_object, uids)
            return self.template()

        self.savepoint = savepoint()
        uids = self.request.form.get("uids", [])
        titles = self.request.form.get("title", [])
        self.created = []
        for index, uid in enumerate(uids):
            title = titles[index]
            object_copy = self.copy_object(uid, title)
            if not object_copy:
                self.savepoint.rollback()
                self.created = []
                break

            self.created.append(api.get_title(object_copy))
        if len(self.created) >= 1:
            message = _("Successfully created: ${items}.",
                        mapping={
                            "items": safe_unicode(
                                ", ".join(self.created))})
        else:
            message = _("No new items were created.")
        self.context.plone_utils.addPortalMessage(message, "info")
        self.request.response.redirect(self.context.absolute_url())
