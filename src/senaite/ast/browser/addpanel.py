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
from Products.Five.browser import BrowserView
from senaite.ast import utils
from senaite.ast.config import DISK_CONTENT_KEY
from senaite.ast.config import RESISTANCE_KEY
from senaite.ast.config import ZONE_SIZE_KEY
from senaite.ast.config import REPORT_KEY


class AddPanelView(BrowserView):
    """View that generates the analyses to be assigned to the context based on
     the configuration of the panel uid from the POST
    """

    def __call__(self):
        # Get the panel
        panel_uid = self.request.form.get("panel_uid")
        panel = api.get_object(panel_uid)

        # Get the objects assigned to the panel
        antibiotics = map(api.get_object, panel.antibiotics)
        microorganisms = map(api.get_object, panel.microorganisms)

        # Exclude those not identified in the current sample
        identified = utils.get_identified_microorganisms(self.context)
        microorganisms = filter(lambda m: m in identified, microorganisms)

        # Create an analysis for each microorganism
        for microorganism in microorganisms:

            # Create/Update the disk content (potency) analysis
            if panel.disk_content:
                self.add_ast_analysis(DISK_CONTENT_KEY, microorganism, antibiotics)

            # Create/Update the zone size analysis
            if panel.zone_size:
                self.add_ast_analysis(ZONE_SIZE_KEY, microorganism, antibiotics)

            # Create/Update the sensitivity result analysis
            self.add_ast_analysis(RESISTANCE_KEY, microorganism, antibiotics)

            # Create/Update the selective reporting analysis
            if panel.selective_reporting:
                self.add_ast_analysis(REPORT_KEY, microorganism, antibiotics)

        return "{} objects affected".format(len(panel.microorganisms))

    @view.memoize
    def get_ast_analyses_info(self):
        """Returns a dict of (title, analyses) with the analyses assigned to
        the current sample
        """
        # Get the existing AST analyses from this sample
        analyses = utils.get_ast_analyses(self.context)

        # Do a mapping title:analysis
        existing = map(api.get_title, analyses)
        return dict(zip(existing, analyses))

    def get_analysis(self, title):
        """Search for an existing and valid AST-like analysis in current sample
        """
        existing = self.get_ast_analyses_info()
        return existing.get(title)

    def add_ast_analysis(self, keyword, microorganism, antibiotics):
        """Updates or creates an ast analysis for the microorganism and
        antibiotics passed-in
        """
        title = utils.get_analysis_title(keyword, microorganism)
        analysis = self.get_analysis(title)
        if analysis:
            # Add new antibiotics to this analysis
            utils.update_ast_analysis(analysis, antibiotics)
            return

        # Create a new analysis
        sample = self.context
        utils.create_ast_analysis(sample, keyword, microorganism, antibiotics)
