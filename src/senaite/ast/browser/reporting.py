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
from bika.lims.interfaces import ISubmitted
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

        # Check whether there are analyses assigned
        analyses = self.get_analyses_for(microorganism, antibiotic)
        analysis = filter(lambda a: a.getKeyword() == REPORT_KEY, analyses)
        analysis = analysis and analysis[-1] or None

        # Set whether reporting is enabled/disabled
        item[uid] = self.is_reporting_enabled(analysis, antibiotic)

        # If sample is not in an editable status, no further actions required
        if not self.can_add_analyses():
            return

        item["allow_edit"].append(uid)
        if not analyses:
            # No analyses assigned for this microorganism
            item.setdefault("disabled", []).append(uid)

        elif analysis and ISubmitted.providedBy(analysis):
            # Analysis assigned, but report info submitted already
            item.setdefault("disable", []).append(uid)

    def is_reporting_enabled(self, analysis, antibiotic):
        """Returns whether the reporting is enabled for the analysis and
        antibiotic passed-in
        """
        if not analysis:
            return False
        interim_fields = analysis.getInterimFields()
        for interim in interim_fields:
            keyword = interim.get("keyword")
            if antibiotic.abbreviation == keyword:
                # choices = "0:|1:Y|2:N"
                return str(interim.get("value")) == "1"
        return False

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
        # Get all the analysis for the given microorganism
        analyses = self.get_analyses_for(microorganism)

        # Get the selective reporting analysis for the given microorganism
        rep_analyses = filter(lambda a: a.getKeyword() == REPORT_KEY, analyses)

        # Check whether selective reporting analysis exists for this micro
        if not rep_analyses:
            # Get the antibiotics assigned for this microorganism
            all_abx = utils.get_antibiotics(analyses)

            # Create the selective reporting analysis
            rep_analyses = [utils.create_ast_analysis(self.context, REPORT_KEY,
                                                      microorganism, all_abx)]

        # Reporting is true for the given antibiotics
        selected = map(lambda o: o.abbreviation, antibiotics)
        for analysis in rep_analyses:
            interim_fields = analysis.getInterimFields()
            for antibiotic in interim_fields:
                keyword = antibiotic.get("keyword")
                # choices = "0:|1:Y|2:N"
                value = "1" if keyword in selected else "2"
                antibiotic.update({
                    "value": value
                })
