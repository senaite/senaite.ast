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
# Copyright 2020-2024 by it's authors.
# Some rights reserved, see README and LICENSE.

import itertools
from datetime import datetime

from bika.lims import api
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from senaite.ast import logger
from senaite.ast import utils
from senaite.ast.calc import update_sensitivity_result
from senaite.ast.config import NOT_TESTED
from senaite.ast.config import REPORT_EXTRAPOLATED_KEY
from senaite.ast.config import REPORT_KEY
from senaite.ast.config import RESISTANCE_KEY
from senaite.core.api import dtime as dt
from senaite.core.browser.modals import Modal


class RejectAntibioticsModal(Modal):
    """Modal that allows to reject antibiotics (flag them as Not Tested)
    """

    template = ViewPageTemplateFile("templates/reject_antibiotics.pt")

    def __call__(self):
        if self.request.form.get("submitted", False):
            self.handle_submit()
        return self.template()

    @property
    def analyses(self):
        """Returns the analyses passed-in as UIDs through the request
        """
        analyses = map(api.get_object_by_uid, self.uids)
        # be sure we rely on AST analyses only
        analyses = filter(utils.is_ast_analysis, analyses)
        # extend with siblings (AST-like analyses from same microorganism)
        siblings = map(utils.get_ast_siblings, analyses)
        siblings = list(itertools.chain.from_iterable(siblings))
        analyses.extend(siblings)
        # remove duplicates
        analyses = set(analyses)
        # exclude analyses meant for selective reporting
        exclude = [REPORT_KEY, REPORT_EXTRAPOLATED_KEY]
        analyses = filter(lambda an: an.getKeyword() not in exclude, analyses)
        return analyses

    @property
    def antibiotics(self):
        """Returns a list of antibiotics with the antibiotics assigned to
        the analyses passed-in as UIDs through the request, sorted by name
        ascending
        """
        kwargs = dict(filter_criteria=self.is_valid_antibiotic)
        antibiotics = utils.get_antibiotics(self.analyses, **kwargs)
        return sorted(antibiotics, key=lambda ab: api.get_title(ab))

    def is_valid_antibiotic(self, interim_field):
        """Returns whether the interim field corresponds to an antibiotic that
        has not been rejected (flagged as not tested)
        """
        if interim_field.get("status_rejected", False):
            return False
        return True

    def handle_submit(self):
        """Handles the form submit. Flag the antibiotics selected in the form
        as Not Tested for all analyses passed-in as UIDs through the request
        """
        # get the uids that have been selected for rejection
        rejected_uids = self.request.get("antibiotics")

        # flag the antibiotic as Not Tested (NT) for each analysis
        for analysis in self.analyses:
            self.reject_antibiotics(analysis, rejected_uids)

    def reject_antibiotics(self, analysis, antibiotics):
        """Flags the antibiotics passed-in for the given analysis as Not tested
        """
        interims = []
        keyword = analysis.getKeyword()
        to_reject = map(api.get_uid, antibiotics)
        for interim in analysis.getInterimFields():
            abx_uid = interim.get("uid")
            if abx_uid in to_reject:

                # set rejected status
                user_id = api.get_current_user().id
                timestamp = dt.to_iso_format(datetime.now())
                interim["status_rejected"] = timestamp
                interim["status_rejected_by"] = user_id

                # set the result value
                self.set_not_tested_result(interim)

            interims.append(interim)

        # update the interims/antibiotics
        analysis.setInterimFields(interims)

        if keyword == RESISTANCE_KEY:
            # Compute all combinations of interim/antibiotic and possible
            # result and generate the result options for this analysis (the
            # "Result" field is never displayed and is only used for reporting)
            result_options = utils.get_result_options(analysis)
            analysis.setResultOptions(result_options)

            # Update the final result to be reported
            update_sensitivity_result(analysis)

    def set_not_tested_result(self, interim):
        """Sets the 'Not tested' result to the interim field. If the interim
        has choices, it uses '0' as the value for the Not Tested. Otherwise,
        sets NT as the textual result
        """
        choices = utils.get_choices(interim)
        if not choices:
            # no choices, set string result
            interim["value"] = NOT_TESTED
            interim["string_result"] = True
            return

        # insert a new choice ("-1", "NT")
        choice = ("-1", NOT_TESTED)
        if choice not in choices:
            choices.insert(0, choice)
            choices = ["{}:{}".format(ch[0], ch[1]) for ch in choices]
            interim["choices"] = "|".join(choices)

        # assign the result value
        interim["value"] = "-1"
        interim["string_result"] = True
