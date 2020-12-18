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
from plone.memoize import view
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from senaite.ast import messageFactory as _
from senaite.ast import utils
from senaite.ast.browser.panel import ASTPanelView
from senaite.ast.config import REPORT_KEY


class ASTPanelReportingView(ASTPanelView):
    """Listing view for selective reporting of AST results. Displays a listing
    where rows are microorganisms and columns antibiotics. A checkbox is
    rendered on each cell, meaning that an AST result for the selected tuple
    microorganism-antibiotic will be reported in results report when checked
    """

    template = ViewPageTemplateFile("templates/ast_reporting.pt")

    def __init__(self, context, request):
        super(ASTPanelReportingView, self).__init__(context, request)
        self.title = _("AST Panel Selective Reporting")
        self.show_search = False

    def before_render(self):
        pass

    def update(self):
        super(ASTPanelReportingView, self).update()

        # Keep the microorganisms assigned to the Sample's AST panel only
        uids = map(api.get_uid, self.get_microorganisms())
        self.contentFilter.update({
            "UID": uids,
        })

    def render_checkbox(self, item, microorganism, antibiotic):
        """Renders the checkbox properties for the item, microorganism and
        antibiotic passed-in
        """
        uid = api.get_uid(antibiotic)
        has_analysis = self.has_analysis_for(microorganism, antibiotic)

        if self.can_add_analyses():
            # The sample is in an editable status
            item["allow_edit"].append(uid)

        item[uid] = has_analysis
        if has_analysis and self.is_editable(microorganism, antibiotic):
            return

        # There is no analysis or is not editable. Disable the checkbox
        item.setdefault("disabled", []).append(uid)

    @view.memoize
    def get_microorganisms(self):
        """Returns the list of microorganism objects assigned to this sample,
        sorted by title ascending
        """
        analyses = self.get_analyses(skip_invalid=True)
        microorganisms = utils.get_microorganisms(analyses)
        return sorted(microorganisms, key=lambda m: api.get_title(m))

    @view.memoize
    def get_antibiotics(self):
        """Returns the list of antibiotics objects assigned to this sample,
        sorted by title ascending
        """
        analyses = self.get_analyses(skip_invalid=True)
        antibiotics = utils.get_antibiotics(analyses)
        return sorted(antibiotics, key=lambda ab: api.get_title(ab))

    def update_analyses(self, microorganism, antibiotics):
        """Update the ast reporting analyses for the given microorganism and
        list of antibiotics
        """
        # Get the selective reporting analysis for the given microorganism
        analyses = self.get_analyses_for(microorganism, skip_invalid=True)
        analyses = filter(lambda a: a.getKeyword() == REPORT_KEY, analyses)
        if not analyses:
            return

        # Reporting is true for the given antibiotics
        selected = map(lambda o: o.abbreviation, antibiotics)
        for analysis in analyses:
            interim_fields = analysis.getInterimFields()
            for antibiotic in interim_fields:
                keyword = antibiotic.get("keyword")
                # choices = "0:|1:Y|2:N"
                value = "1" if keyword in selected else "2"
                antibiotic.update({
                    "value": value
                })
