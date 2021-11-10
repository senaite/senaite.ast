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

from bika.lims import api
from bika.lims.catalog import SETUP_CATALOG
from bika.lims.interfaces import IInternalUse
from bika.lims.interfaces import IAuditable
from bika.lims.interfaces import ISubmitted
from senaite.ast import messageFactory as _
from senaite.ast import utils
from senaite.ast.config import BREAKPOINTS_TABLE_KEY
from senaite.ast.config import IDENTIFICATION_KEY
from senaite.ast.config import REPORT_KEY
from senaite.ast.config import RESISTANCE_KEY
from senaite.ast.config import ZONE_SIZE_KEY
from senaite.ast.interfaces import IASTAnalysis
from senaite.ast.utils import get_microorganism
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


def handle_auto_category(analysis):
    """Handles the automatic assignment of the result for the sensitivity
    testing category analysis (ast_resistance) based on the value set for both
    the diameter zone in mm and the breakpoints table, if any
    """
    import pdb;pdb.set_trace()
    keywords = [BREAKPOINTS_TABLE_KEY, ZONE_SIZE_KEY]
    keyword = analysis.getKeyword()
    if keyword not in keywords:
        return

    def get_by_keyword(analyses_in, service_keyword):
        for an in analyses_in:
            if an.getKeyword() == service_keyword:
                return an
        return None

    # Get the AST siblings for same sample and microorganism
    siblings = utils.get_ast_siblings(analysis)

    # Extract the analysis that stores the sensitivity category
    resistance_analysis = get_by_keyword(siblings, RESISTANCE_KEY)
    if ISubmitted.providedBy(resistance_analysis):
        # Sensitivity category submitted already, nothing to do here!
        return

    # Extract the counterpart analysis
    submitted = filter(ISubmitted.providedBy, siblings)
    analyses = submitted + [analysis]
    breakpoints_analysis = get_by_keyword(analyses, BREAKPOINTS_TABLE_KEY)
    zone_sizes_analysis = get_by_keyword(analyses, ZONE_SIZE_KEY)
    if not all([breakpoints_analysis, zone_sizes_analysis]):
        return

    # The result for each antibiotic is stored as an interim field
    breakpoints = breakpoints_analysis.getInterimFields()
    zone_sizes = zone_sizes_analysis.getInterimFields()
    categories = resistance_analysis.getInterimFields()

    # Get the mapping of Antibiotic -> BreakpointsTable
    breakpoints = dict(map(lambda b: (b['uid'], b['value']), breakpoints))

    # Get the mapping of Antibiotic -> Zone sizes
    zone_sizes = dict(map(lambda z: (z['uid'], z['value']), zone_sizes))

    # Get the microorganism this analysis is associated to
    microorganism = get_microorganism(analysis)
    microorganism_uid = api.get_uid(microorganism)

    # Update sensitivity categories
    for category in categories:
        antibiotic_uid = category["uid"]

        breakpoint = breakpoints.get(antibiotic_uid)
        if breakpoint == "0":
            # Default N/A breakpoint defined
            continue

        zone_size = zone_sizes.get(antibiotic_uid)
        if not zone_size:
            # No zone size entered yet
            continue

        # Findout the category by looking to the breakpoints table
        zone_size = api.to_float(zone_size)
        break_obj = api.get_object(breakpoint)
        for val in break_obj.breakpoints:
            if val.get("antibiotic") != antibiotic_uid:
                continue
            if val.get("microorganism") != microorganism_uid:
                continue

            # Choices for sensitivity category 0:|1:S|2:I|3:R
            diameter_s = api.to_float(val.get("diameter_s"))
            diameter_r = api.to_float(val.get("diameter_r"))
            if zone_size < diameter_r:
                category.update({"value": "3"})
            elif zone_size >= diameter_s:
                category.update({"value": "1"})

    resistance_analysis.setInterimFields(categories)


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

    # Handles the automatic calculation of sensitivity categories
    handle_auto_category(analysis)

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

    # Results are the values (R/S/+/-) set for resistance' interim fields
    results = resistance.getInterimFields()

    # Find out the resistance results to report
    report_analysis = filter(lambda an: an.getKeyword() == REPORT_KEY, analyses)
    if report_analysis:
        # The results to be reported are defined by the Y/N values set for the
        # interim fields of the "selective reporting" analysis
        to_report = report_analysis[0].getInterimFields()

        # XXX senaite.app.listing has no support boolean type for interim fields
        to_report = filter(lambda k: k.get("value") == "1", to_report)

        # Get the abbreviation of microorganisms (keyword)
        keywords = map(lambda k: k.get("keyword"), to_report)

        # Filter the interim fields from resistance
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


def after_retest(analysis):
    """Event fired when an analysis is retested
    """
    if not IASTAnalysis.providedBy(analysis):
        return

    source = analysis.getRetestOf()
    if not source:
        return

    # Set the original interim fields to the retest
    copy_interims(source, analysis)


def after_retract(analysis):
    """Event fired when an analysis is retracted
    """
    if not IASTAnalysis.providedBy(analysis):
        return

    # The original analysis is the one being retracted
    retest = analysis.getRetest()
    if not retest:
        return

    # Set the original interim fields to the new analysis
    copy_interims(analysis, retest)


def copy_interims(source, destination):
    """Copies the interims from the source analysis to destination analysis
    """
    interim_fields = copy.deepcopy(source.getInterimFields())
    map(lambda interim: interim.update({"value": ""}), interim_fields)
    destination.setInterimFields(interim_fields)
