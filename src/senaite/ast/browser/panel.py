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
from bika.lims.catalog import SETUP_CATALOG
from bika.lims.interfaces import ISubmitted
from bika.lims.interfaces import IVerified
from bika.lims.utils import changeWorkflowState
from bika.lims.utils import get_link_for
from plone.memoize import view
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from senaite.app.listing.view import ListingView
from senaite.ast import messageFactory as _
from senaite.ast import utils
from senaite.ast.config import BREAKPOINTS_TABLE_KEY
from senaite.ast.config import RESISTANCE_KEY
from senaite.ast.config import ZONE_SIZE_KEY
from senaite.core.workflow import ANALYSIS_WORKFLOW
from zope.interface import noLongerProvides


class ASTPanelView(ListingView):
    """Listing view that represents the configuration of an AST Panel,
    displaying microorganisms as rows and antibiotics as rows. A checkbox is
    rendered on each cell, meaning that an AST result will be expected for
    that microorganism-antibiotic tuple
    """

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
                "title": _("All microorganisms"),
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
        antibiotics = map(self.get_object, uids)

        # Generate a transposed dict microorganism->antibiotics
        # Add all microorganisms, so analyses without any antibiotic selected
        # can also be removed
        microorganisms = self.get_microorganisms()
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
        analyses = self.get_analyses_for(microorganism)

        # AST-analyses are inter-dependent, so a given antibiotic cannot be
        # removed unless none of the analyses have a submitted result for it
        required = self.get_required_antibiotics(microorganism)
        selected = filter(lambda ab: ab not in required, antibiotics)
        antibiotics = required + selected

        if not analyses:
            if antibiotics:
                # Create new analyses
                keys = [BREAKPOINTS_TABLE_KEY, ZONE_SIZE_KEY, RESISTANCE_KEY]
                utils.create_ast_analyses(self.context, keys, microorganism,
                                          antibiotics)

        elif not antibiotics:
            # Remove analyses that can be deleted
            analyses = filter(self.can_delete, analyses)
            analyses_ids = map(api.get_id, analyses)
            map(self.context._delObject, analyses_ids)  # noqa

        else:
            # Update analyses
            for analysis in analyses:
                self.update_analysis(analysis, antibiotics)

    def can_delete(self, analysis):
        """Returns whether the analysis can be removed or not
        """
        if ISubmitted.providedBy(analysis):
            return False

        if IVerified.providedBy(analysis):
            return False

        for interim in analysis.getInterimFields():
            if not utils.is_interim_editable(interim):
                return False

        return True

    def update_analysis(self, analysis, antibiotics):
        """Updates the analysis with the antibiotics
        """
        if ISubmitted.providedBy(analysis):
            noLongerProvides(analysis, ISubmitted)

        if IVerified.providedBy(analysis):
            noLongerProvides(analysis, IVerified)

        # Rollback to assigned/unassigned status
        to_rollback = ["verified", "to_be_verified"]
        if api.get_review_status(analysis) in to_rollback:
            get_prev_status = api.get_previous_worfklow_status_of
            prev_status = get_prev_status(analysis, skip=to_rollback)
            changeWorkflowState(analysis, ANALYSIS_WORKFLOW, prev_status)

        # Update the analysis with the antibiotics
        utils.update_ast_analysis(analysis, antibiotics, purge=True)

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
        if self.can_add_analyses():
            item["allow_edit"].append(uid)

            # Render the checkbox as disabled/enabled
            disabled = item.get("disabled", None)
            if not isinstance(disabled, (list, tuple)):
                item["disabled"] = []

            if has_analysis and not self.is_editable(microorganism, antibiotic):
                item.setdefault("disabled", []).append(uid)

    def is_editable(self, microorganism, antibiotic):
        """Returns whether all results of AST analyses for the microorganism
        and antibiotic passed in are editable
        """
        antibiotics = self.get_required_antibiotics(microorganism)
        return antibiotic not in antibiotics

    def has_analysis_for(self, microorganism, antibiotic):
        """Returns whether there are ast analyses for this microorganism,
         antibiotic and current context
         """
        analyses = self.get_analyses_for(microorganism, antibiotic,
                                         skip_invalid=False)
        return len(analyses) > 0

    def get_analyses_for(self, microorganism=None, antibiotic=None,
                         skip_invalid=True):
        """Returns the ast-analyses for this microorganism, antibiotic and
        current context, if any
        """
        ans = self.get_analyses(skip_invalid=skip_invalid)

        # Microorganism name is the ShortTitle
        if microorganism:
            micro_title = api.get_title(microorganism)
            ans = filter(lambda a: a.getShortTitle() == micro_title, ans)

        # Antibiotic is defined as an interim
        if antibiotic:
            ans = filter(lambda a: self.has_antibiotic(a, antibiotic), ans)

        return ans

    def get_required_antibiotics(self, microorganism):
        """Returns the list of antibiotics that cannot be removed from analyses
        for the given microorganism because there is at least one AST analysis
        with a result set for them
        """
        def is_required(interim):
            return not utils.is_interim_editable(interim)

        analyses = self.get_analyses_for(microorganism=microorganism)
        return utils.get_antibiotics(analyses, filter_criteria=is_required)

    def has_antibiotic(self, analysis, antibiotic):
        """Returns whether the analysis has the specified antibiotic assigned.
        Extrapolated antibiotics are not considered
        """
        for interim in analysis.getInterimFields():
            if utils.is_extrapolated_interim(interim):
                # Skip extrapolated antibiotics
                continue
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
    def get_analyses(self, skip_invalid=False):
        """Returns the list of ast-like analyses from current context
        """
        return utils.get_ast_analyses(self.context, skip_invalid=skip_invalid)

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

    @view.memoize
    def get_microorganisms(self):
        """Returns the list of microorganisms registered in the system
        """
        return api.search(self.contentFilter, self.catalog)

    @view.memoize
    def can_add_analyses(self):
        """Returns whether the status of context allows to add analyses or not
        """
        if IVerified.providedBy(self.context):
            return False
        return api.is_active(self.context)

    def get_children_hook(self, parent_uid, child_uids=None):
        return super(ASTPanelView, self).get_children_hook(
            parent_uid, child_uids=child_uids)
