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
from bika.lims import api
from bika.lims.interfaces import IAnalysis
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from senaite.ast import logger
from senaite.ast import utils
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
        # include the siblings (ast analyses from same microorganism)
        siblings = map(utils.get_ast_siblings, analyses)
        # flatten the list of siblings
        siblings = list(itertools.chain.from_iterable(siblings))
        analyses.extend(siblings)
        return filter(IAnalysis.providedBy, set(analyses))

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
        not_tested = map(api.get_uid, antibiotics)
        for interim in analysis.getInterimFields():
            abx_uid = interim.get("uid")
            if abx_uid in not_tested:
                logger.info("{}:{} Flagged as rejected".format(
                    api.get_title(analysis), interim.get("keyword")
                ))
                interim["status_rejected"] = True

            interims.append(interim)

        analysis.setInterimFields(interims)
