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
from Products.Five.browser import BrowserView
from senaite.ast import utils


class AddPanelView(BrowserView):
    """View that generates the analyses to be assigned to the context based on
     the configuration of the panel uid from the POST
    """

    def __call__(self):
        # Get the panel
        panel_uid = self.request.form.get("panel_uid")
        panel = api.get_object(panel_uid)

        # Convert the antibiotics assigned to interims
        antibiotics = map(utils.to_interim, panel.antibiotics)

        # Get the existing AST analyses from this sample
        analyses = self.context.getAnalyses(getPointOfCapture="ast")
        analyses = map(api.get_object, analyses)

        # Skip those that are invalid
        skip = ["cancelled", "retracted", "rejected"]
        analyses = filter(lambda a: api.get_review_status(a) not in skip,
                          analyses)

        # Do a mapping title:analysis
        existing = map(api.get_title, analyses)
        existing = dict(zip(existing, analyses))

        # Create an analysis for each microorganism
        for microorganism in panel.microorganisms:
            microorganism = api.get_object(microorganism)

            # Check if there is already an analysis for this microorganism
            title = api.get_title(microorganism)
            analysis = existing.get(title)
            if analysis:
                # Add the new antibiotics to this analysis
                utils.update_ast_analysis(analysis, antibiotics)
                continue

            # Create a new analysis
            utils.create_ast_analysis(self.context, microorganism, antibiotics)

        return "{} objects created".format(len(panel.microorganisms))
