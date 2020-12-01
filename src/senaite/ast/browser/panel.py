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

import collections

from bika.lims import api
from bika.lims import senaiteMessageFactory as _sc
from bika.lims.catalog import CATALOG_ANALYSIS_LISTING
from bika.lims.catalog import SETUP_CATALOG
from bika.lims.interfaces import ISubmitted
from bika.lims.utils import get_link_for
from plone.memoize import view
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from senaite.app.listing.view import ListingView
from senaite.ast import messageFactory as _
from senaite.ast import utils
from senaite.ast.config import RESISTANCE_KEY
from senaite.ast.config import ZONE_SIZE_KEY
from senaite.ast.config import REPORT_KEY


class ASTPanelView(ListingView):

    template = ViewPageTemplateFile("templates/ast_panel.pt")

    def __init__(self, context, request):
        super(ASTPanelView, self).__init__(context, request)

        self.title = _("AST Panel")
        self.catalog = SETUP_CATALOG
        self.contentFilter = {
            "portal_type": "Microorganism",
            "is_active": True,
            "sort_on": "sortable_title",
            "sort_order": "ascending",
        }
        self.omit_form = True
        self.show_search = True
        self.show_select_column = False
        self.show_categories = False
        self.show_column_toggles = False
        self.fetch_transitions_on_select = False
        self.show_workflow_action_buttons = False

        # Only the first column is defined here, the rest of columns, that are
        # the antibiotics abbreviations are added dynamically
        self.columns = collections.OrderedDict((
            ("Microorganism", {
                "title": _("Microorganism"),
            }),
        ))

        self.review_states = [
            {
                "id": "default",
                "title": _sc("All microorganisms"),
                "contentFilter": {},
                "columns": self.columns.keys(),
            }
        ]

    def __call__(self, *args, **kwargs):
        # Form submit toggle
        form = self.request.form
        form_submitted = form.get("submitted", False)
        if not form_submitted:
            return super(ASTPanelView, self).__call__()

        # Form submitted
        button_submit = form.get("button_submit", False)
        if form_submitted and button_submit:
            return self.handle_save()

        return self.redirect()

    def handle_save(self):
        """Handles the save action
        """
        form = self.request.form

        # Key uids are antibiotics (columns)
        uids = filter(api.is_uid, form.keys())
        antibiotics = map(api.get_object_by_uid, uids)

        # Generate a transposed dict microorganism->antibiotics
        microorganisms = api.search(self.contentFilter, self.catalog)
        mapping = dict(map(lambda m: (api.get_uid(m), []), microorganisms))
        for antibiotic in antibiotics:
            abx_uid = api.get_uid(antibiotic)
            for uid in form[abx_uid].keys():
                mapping.setdefault(uid, []).append(antibiotic)

        # Update existing analyses and create new ones
        for uid, abx in mapping.items():
            microorganism = self.get_object(uid)
            self.update_analyses(microorganism, abx)

        return self.redirect(_("AST analyses updated"))

    def update_analyses(self, microorganism, antibiotics):
        analyses = self.get_analyses_for(microorganism, skip_invalid=True)

        # Filter those that are not yet submitted
        analyses = filter(lambda a: not ISubmitted.providedBy(a), analyses)

        if not analyses:
            if antibiotics:
                # Create new analyses
                keywords = [ZONE_SIZE_KEY, RESISTANCE_KEY, REPORT_KEY]
                utils.create_ast_analyses(self.context, keywords, microorganism,
                                          antibiotics)

        elif not antibiotics:
            # Remove analyses
            analyses_ids = map(api.get_id, analyses)
            map(self.context._delObject, analyses_ids)  # noqa

        else:
            # Update analyses
            map(lambda a:
                utils.update_ast_analysis(a, antibiotics, remove=True),
                analyses)

    def redirect(self, message=None, level="info"):
        """Redirect with a message
        """
        redirect_url = api.get_url(self.context)
        if message is not None:
            self.context.plone_utils.addPortalMessage(message, level)
        return self.request.response.redirect(redirect_url)

    def update(self):
        super(ASTPanelView, self).update()

        # Add the antibiotics abbreviations as columns
        for antibiotic in self.get_antibiotics():
            uid = api.get_uid(antibiotic)
            self.columns[uid] = {
                "title": antibiotic.abbreviation,
                "type": "boolean",
            }
        self.review_states[0]["columns"] = self.columns.keys()

    def folderitem(self, obj, item, index):
        microorganism = api.get_object(obj)
        item["Microorganism"] = get_link_for(obj, tabindex="-1")

        # Fill the rest of columns (antibiotics)
        abx_uids = filter(lambda c: c != "Microorganism", self.columns.keys())
        for uid in abx_uids:
            antibiotic = self.get_antibiotic(uid)
            self.render_checkbox(item, microorganism, antibiotic)

        return item

    def render_checkbox(self, item, microorganism, antibiotic):
        """Renders the checkbox properties for the item, microorganism and
        antibiotic passed-in
        """
        uid = api.get_uid(antibiotic)
        has_analysis = self.has_analysis_for(microorganism, antibiotic)
        item[uid] = has_analysis
        item["allow_edit"].append(uid)
        if has_analysis and not self.is_editable(microorganism, antibiotic):
            item.setdefault("disabled", []).append(uid)

    def is_editable(self, microorganism, antibiotic):
        """Returns whether there are submitted analyses for this microorganism,
        antibiotic and current context
        """
        analyses = self.get_analyses_for(microorganism, antibiotic)
        analyses = filter(ISubmitted.providedBy, analyses)
        return len(analyses) == 0

    def has_analysis_for(self, microorganism, antibiotic):
        """Returns whether there are ast analyses for this microorganism,
         antibiotic and current context
         """
        analyses = self.get_analyses_for(microorganism, antibiotic)
        return len(analyses) > 0

    def get_analyses_for(self, microorganism=None, antibiotic=None,
                         skip_invalid=False):
        """Returns the ast-analyses for this microorganism, antibiotic and
        current context, if any
        """
        ans = self.get_analyses()

        # Microorganism name is the ShortTitle
        if microorganism:
            micro_title = api.get_title(microorganism)
            ans = filter(lambda a: a.getShortTitle() == micro_title, ans)

        # Antibiotic is defined as an interim
        if antibiotic:
            ans = filter(lambda a: self.has_antibiotic(a, antibiotic), ans)

        # Skip invalids
        skip = skip_invalid and ["cancelled", "retracted", "rejected"] or []
        ans = filter(lambda a: api.get_review_status(a) not in skip, ans)

        return ans

    def has_antibiotic(self, analysis, antibiotic):
        """Returns whether the analysis has the specified antibiotic assigned
        """
        for interim in analysis.getInterimFields():
            if interim.get("keyword") == antibiotic.abbreviation:
                return True
        return False

    @view.memoize
    def get_object(self, uid):
        """Returns an object for the given uid
        """
        return api.get_object_by_uid(uid)

    @view.memoize
    def get_antibiotic(self, uid):
        """Returns the antibiotic object for the given uid
        """
        antibiotics = self.get_antibiotics()
        antibiotic = filter(lambda a: api.get_uid(a) == uid, antibiotics)
        return antibiotic[0]

    @view.memoize
    def get_analyses(self):
        """Returns the list of ast-like analyses from current context
        """
        query = {
            "portal_type": "Analysis",
            "getPointOfCapture": "ast",
            "getAncestorsUIDs": [api.get_uid(self.context)],
        }
        brains = api.search(query, CATALOG_ANALYSIS_LISTING)
        return map(api.get_object, brains)

    @view.memoize
    def get_antibiotics(self):
        """Returns the active antibiotics registered in the system, sorted by
        title ascending
        """
        query = {
            "portal_type": "Antibiotic",
            "is_active": True,
            "sort_on": "sortable_title",
            "sort_order": "ascending",
        }
        brains = api.search(query, SETUP_CATALOG)
        return map(api.get_object, brains)

    def get_children_hook(self, parent_uid, child_uids=None):
        return super(ASTPanelView, self).get_children_hook(
            parent_uid, child_uids=child_uids)
