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

import json
from collections import OrderedDict

from bika.lims import api
from bika.lims.browser.analyses import AnalysesView
from bika.lims.interfaces import IVerified
from bika.lims.utils import get_image
from bika.lims.utils import get_link
from plone.memoize import view
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from senaite.ast import is_installed
from senaite.ast import messageFactory as _
from senaite.ast import utils
from senaite.ast.config import AST_POINT_OF_CAPTURE
from senaite.ast.config import IDENTIFICATION_KEY
from senaite.ast.utils import get_ast_analyses
from senaite.ast.i18n import translate as t
from senaite.core.browser.viewlets.sampleanalyses import LabAnalysesViewlet


class ASTAnalysesViewlet(LabAnalysesViewlet):
    """AST Analyses section viewlet for Sample view
    """
    title = _("Antibiotic Sensitivities")
    icon_name = "ast_panel"
    capture = AST_POINT_OF_CAPTURE

    def available(self):
        """Returns true if senaite.ast is installed and the sample contains
        at least one sensitivity testing analysis or the microorganism
        identification analysis is present
        """
        if not is_installed():
            return False

        # does this sample has the identification analysis?
        analyses = self.context.getAnalyses(getKeyword=IDENTIFICATION_KEY)
        if analyses:
            return True

        # does this have sensitivity testing analyses?
        ast_analyses = get_ast_analyses(self.context)
        if ast_analyses:
            return True

        return False

    def is_collapsed(self):
        return False


class ManageResultsView(AnalysesView):
    """Listing view for AST results entry
    """
    contents_table_template = ViewPageTemplateFile("templates/ast_results.pt")

    def __init__(self, context, request):
        super(ManageResultsView, self).__init__(context, request)

        self.contentFilter.update({
            "getPointOfCapture": AST_POINT_OF_CAPTURE,
            "getAncestorsUIDs": [api.get_uid(context)],
            "sort_on": "sortable_title",
            "sort_order": "ascending",
        })

        self.form_id = "ast_analyses"
        self.allow_edit = True
        self.show_workflow_action_buttons = True
        self.show_search = False

        # Add the Microorganism column
        new_columns = (
            ("Microorganism", {
                "title": _("Microorganism"),
                "sortable": False}),
        )
        old_columns = self.columns.items()
        self.columns = OrderedDict(list(new_columns) + list(old_columns))
        self.columns["Service"].update({
            "title": _("Result"),
        })

        # Remove the columns we are not interested in from review_states
        hide = ["Method", "Instrument", "Analyst", "DetectionLimitOperand",
                "Specification", "Uncertainty", "retested", "Attachments",
                "DueDate", "Result", "Hidden", "Unit"]

        all_columns = self.columns.keys()
        all_columns = filter(lambda c: c not in hide, all_columns)
        for review_state in self.review_states:
            review_state.update({"columns": all_columns})

    @view.memoize
    def get_service_id(self, service_uid_brain_object):
        obj = api.get_object(service_uid_brain_object)
        return api.get_id(obj)

    def analysis_categories_enabled(self):
        """Returns false, as analyses for AST results entry cannot be
        categorized, cause all them are computed
        """
        return False

    def folderitem(self, obj, item, index):
        keyword = obj.getKeyword
        item["Keyword"] = keyword
        item["service_uid"] = obj.getServiceUID

        # The analysis title is made of Microorganism plus the name of the
        # analysis type (diameter, etc.), separated by '-'.
        # E.g.:
        #   Escherichia coli - Zone size (mm)
        # Therefore, we need to take into consideration the possibility of
        # having that same separator '-' in the Microorganism's name.
        # E.g.:
        #   Escherichia coli (meropenem-resistant - CRE) - Zone size (mm)
        tokens = obj.Title.split("-")
        item["Microorganism"] = "-".join(tokens[:-1]).strip()
        item["Service"] = tokens[-1].strip()
        item['class']['service'] = 'service_title'

        # This is used for sorting
        sort_key = "{}:{}".format(item["Microorganism"], format(index, '05d'))
        item["sort_key"] = sort_key

        # Append info link before the service
        # see: bika.lims.site.coffee for the attached event handler
        item["before"]["Service"] = get_link(
            "analysisservice_info?service_uid={}&analysis_uid={}"
            .format(obj.getServiceUID, obj.UID),
            value="<i class='fas fa-info-circle'></i>",
            css_class="overlay_panel", tabindex="-1")

        # Fill item's row class
        self._folder_item_css_class(obj, item)
        # Fill result and/or result options
        self._folder_item_result(obj, item)
        # Fill calculation and interim fields
        self._folder_item_calculation(obj, item)
        # Fill submitted by
        self._folder_item_submitted_by(obj, item)
        # Fill Partition
        self._folder_item_partition(obj, item)
        # Fill verification criteria
        self._folder_item_verify_icons(obj, item)
        # Fill worksheet anchor/icon
        self._folder_item_assigned_worksheet(obj, item)
        # Fill hidden field (report visibility)
        self._folder_item_report_visibility(obj, item)
        # Renders remarks toggle button
        self._folder_item_remarks(obj, item)
        # Render the interim fields (readonly, editable)
        self.folder_interim_fields(obj, item)

        return item

    def folder_interim_fields(self, obj, item):
        analysis_obj = self.get_object(obj)
        for interim_field in analysis_obj.getInterimFields():
            if utils.is_interim_editable(interim_field):
                continue

            # Remove this interim field from editable fields
            keyword = interim_field["keyword"]
            editable = filter(lambda it: it != keyword, item["allow_edit"])
            item["allow_edit"] = editable

            # This interim will be displayed as readonly mode, display text
            text = utils.get_interim_text(interim_field, default="")
            if interim_field.get("status_rejected", False):
                icon = get_image('warning.png', title=t(_("Not tested")))
                text = "{}{}".format(text, icon)
            item["replace"][keyword] = text or "&nbsp;"

    def folderitems(self):
        # This shouldn't be required here, but there are some views that calls
        # directly contents_table() instead of __call__, so before_render is
        # never called. :(
        self.before_render()

        # Get all items
        # Note we call AnalysesView's base class!
        items = super(AnalysesView, self).folderitems()

        # TAL requires values for all interim fields on all items, so we set
        # blank values in unused cells
        for item in items:
            for field in self.interim_columns:
                if field not in item:
                    item[field] = ""

        # Add InterimFields keys (Antibiotic abbreviations) to columns
        interim_keys = self.interim_columns.keys()
        interim_keys.reverse()
        for col_id in interim_keys:
            if col_id not in self.columns:
                self.columns[col_id] = {
                    "title": self.interim_columns[col_id],
                    "input_width": "2",
                    "input_class": "ajax_calculate string",
                    "sortable": False,
                    "toggle": True,
                    "ajax": True,
                }

        if self.allow_edit:
            new_states = []
            for state in self.review_states:
                # Resort interim fields
                columns = state["columns"]
                position = columns.index("Service") + 1
                for col_id in interim_keys:
                    if col_id not in columns:
                        columns.insert(position, col_id)

                state.update({"columns": columns})
                new_states.append(state)

            self.review_states = new_states
            self.show_select_column = True

        self.json_interim_fields = json.dumps(self.interim_fields)

        # Sort items
        items = sorted(items, key=lambda it: it["sort_key"])

        # Group items by organism
        self.group_by_microorganism(items)

        return items

    def group_by_microorganism(self, items):
        """Groups the items by microorganism, adding a rowspan to the first
        cell of the row
        """
        def apply_rowspan(item, rowspan):
            remarks = self.is_analysis_remarks_enabled()
            rowspan = remarks and rowspan * 2 or rowspan
            item["rowspan"] = {"Microorganism": rowspan}

        rowspan = 1
        first_item = None
        for item in items:
            if not first_item:
                first_item = item
                continue

            if first_item.get("Microorganism") != item.get("Microorganism"):
                apply_rowspan(first_item, rowspan)
                first_item = item
                rowspan = 1
                continue

            # Skip this cell (included in the first item rowspan)
            item["skip"] = ["Microorganism"]
            rowspan += 1

        if first_item and rowspan > 1:
            apply_rowspan(first_item, rowspan)

    @view.memoize
    def is_analysis_remarks_enabled(self):
        """Check if analysis remarks are enabled
        """
        return api.get_setup().getEnableAnalysisRemarks()

    def get_children_hook(self, parent_uid, child_uids=None):
        """Hook to get the children of an item
        """
        super(ManageResultsView, self).get_children_hook(
            parent_uid, child_uids=child_uids)

    @view.memoize
    def get_panels(self):
        """Returns a list of dict elements each one representing a panel, sorted
        by title ascending. Each panel has at least one of the microorganisms
        identified in the current sample
        :return: a list of dicts
        """
        # Get the identified microorganisms for this Sample
        microorganisms = utils.get_identified_microorganisms(self.context)

        # Get the panels with at least of these microorganisms assigned
        panels = utils.get_panels_for(microorganisms)
        return map(self.get_panel_info, panels)

    def get_panel_info(self, brain_or_object):
        return {
            "uid": api.get_uid(brain_or_object),
            "title": api.get_title(brain_or_object),
        }

    def can_add_analyses(self):
        """Returns whether the status of context allows to add analyses or not
        """
        if IVerified.providedBy(self.context):
            return False
        return api.is_active(self.context)
