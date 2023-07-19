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
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.utils import safe_unicode
from Products.Five import BrowserView
from senaite.ast.utils import copy_service
from transaction import savepoint


class DuplicateView(BrowserView):
    """Displays a list of object in a table to duplicate.
    """
    created = []

    def __call__(self):
        uc = getToolByName(self.context, "uid_catalog")
        if "copy_form_submitted" not in self.request:
            uids = self.request.form.get("uids", [])
            self.services = []
            for uid in uids:
                proxies = uc(UID=uid)
                if proxies:
                    self.services.append(proxies[0].getObject())
            return self.template()
        else:
            self.savepoint = savepoint()
            sources = self.request.form.get("uids", [])
            titles = self.request.form.get("title", [])
            self.created = []
            for i, s in enumerate(sources):
                if not titles[i]:
                    message = _("Validation failed: title is required")
                    message = safe_unicode(message)
                    self.context.plone_utils.addPortalMessage(message, "info")
                    self.savepoint.rollback()
                    self.created = []
                    break
                service_copy = copy_service(s, titles[i])
                if service_copy:
                    self.created.append(api.get_title(service_copy))
            if len(self.created) >= 1:
                message = _("Successfully created: ${items}.",
                            mapping={
                                "items": safe_unicode(
                                    ", ".join(self.created))})
            else:
                message = _("No new items were created.")
            self.context.plone_utils.addPortalMessage(message, "info")
            self.request.response.redirect(self.context.absolute_url())
