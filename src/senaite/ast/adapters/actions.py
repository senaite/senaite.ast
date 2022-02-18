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

import copy

from bika.lims import senaiteMessageFactory as _s
from bika.lims.browser.workflow import WorkflowActionGenericAdapter
from senaite.ast import utils
from senaite.core.api import dtime as dt
from datetime import datetime
from bika.lims import api


class WorkflowActionVerifyAdapter(WorkflowActionGenericAdapter):
    """Adapter in charge of verify action. Adds a "verified"
    attribute to interim fields with result, so user won't be able to modify
    the result if the analysis is rolled back afterwards because of the addition
    of new antibiotics to existing microorganisms
    """

    def __call__(self, action, objects):
        import pdb;pdb.set_trace()
        transitioned = self.do_action(action, objects)
        if not transitioned:
            return self.redirect(message=_s("No changes made"), level="warning")

        # Add attribute "verified" to AST-analysis' interims, so user won't be
        # able to modify the result if the analysis is rolled back afterwards
        # because of the addition of new antibiotics to existing microorganisms
        ast_analyses = filter(utils.is_ast_analysis, transitioned)
        map(self.verify_interims, ast_analyses)

        # Redirect the user to success page
        return self.success(transitioned)

    def verify_interims(self, analysis):
        """Sets a 'verified' interim with current date time to all interim
        fields of this analysis
        """
        user_id = api.get_current_user().id
        verified = dt.to_iso_format(datetime.now())
        interim_fields = copy.deepcopy(analysis.getInterimFields())
        for interim_field in interim_fields:
            interim_field.update({
                "verified": verified,
                "verified_by": user_id})
        analysis.setInterimFields(interim_fields)
