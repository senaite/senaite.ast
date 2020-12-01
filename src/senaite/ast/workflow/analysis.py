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
from bika.lims.catalog import SETUP_CATALOG
from bika.lims.interfaces import IInternalUse
from bika.lims.interfaces import IAuditable
from bika.lims.interfaces import ISubmitted
from senaite.ast import messageFactory as _
from senaite.ast import utils
from senaite.ast.config import IDENTIFICATION_KEY
from senaite.ast.config import REPORT_KEY
from senaite.ast.config import RESISTANCE_KEY
from senaite.ast.interfaces import IASTAnalysis
from zope.interface import alsoProvides
from zope.interface import noLongerProvides


def after_initialize(analysis):
    """Event fired when an analysis is initialized
    """
    if analysis.getKeyword() != IDENTIFICATION_KEY:
        return

    # Get the names list of active microorganisms
    query = {"portal_type": "Microorganism", "is_active": True}
    names = sorted(map(api.get_title, api.search(query, SETUP_CATALOG)))

    # Maybe no microorganisms where identified
    names.insert(0, _("No culture growth obtained"))

    # Generate the analysis result options
    options = zip(range(len(names)), names)
    options = map(lambda m: {"ResultValue": m[0], "ResultText": m[1]}, options)
    analysis.setResultOptions(options)
    analysis.setResultOptionsType("multiselect")
    analysis.reindexObject()


def after_submit(analysis):
    """Event fired when an analysis result gets submitted
    """
    if not IASTAnalysis.providedBy(analysis):
        return

    # Check that values for all interim fields are set
    interim_fields = analysis.getInterimFields()
    values = map(lambda interim: interim.get("value"), interim_fields)
    if not all(values):
        return

    # All siblings for same microorganism and sample have to be submitted
    siblings = utils.get_ast_siblings(analysis)
    submitted = map(ISubmitted.providedBy, siblings)
    if not all(submitted):
        return

    # Calculate the hidden analyses and results
    analyses = siblings + [analysis]

    # We only do report results from "resistance" analysis
    resistance = filter(lambda an: an.getKeyword() == RESISTANCE_KEY, analyses)
    resistance = resistance[0]

    # Results are the values (R/S/+/-) set for resistance analysis interims
    results = resistance.getInterimFields()

    # Find out the resistance results to report
    report_analysis = filter(lambda an: an.getKeyword() == REPORT_KEY, analyses)
    if report_analysis:
        # The results to be reported are defined by the Y/N values set for the
        # interim fields of the "selective reporting" analysis
        to_report = report_analysis[0].getInterimFields()

        # XXX make senaite.app.listing to support boolean type for interims
        to_report = filter(lambda k: k.get("formatted_value") == "Y", to_report)

        # Get the abbreviation of micoorganisms (keyword)
        keywords = map(lambda k: k.get("keyword"), to_report)

        # Filter the interims from resistance
        results = filter(lambda r: r.get("keyword") in keywords, results)

    # The "selected" result options are those to be reported
    options = resistance.getResultOptions()

    def to_report(option):
        key = option.get("InterimKeyword")
        val = option.get("InterimValue")
        for target in results:
            if key == target.get("keyword") and val == target.get("value"):
                return True
        return False

    # Remove the antibiotics to not report from options
    options = filter(to_report, options)

    # The final result is a list with result option values
    result = map(lambda o: o.get("ResultValue"), options)

    # No need to keep track of this in audit (this is internal)
    noLongerProvides(resistance, IAuditable)

    # Set the final result
    capture_date = resistance.getResultCaptureDate()
    resistance.setResult(result)
    resistance.setResultCaptureDate(capture_date)

    # We do want to report this resistance analysis
    if IInternalUse.providedBy(resistance):
        noLongerProvides(resistance, IInternalUse)

    # Re-enable the audit for this analysis
    alsoProvides(resistance, IAuditable)
