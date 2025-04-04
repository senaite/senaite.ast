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
from bika.lims import api
from bika.lims.interfaces import IAuditable
from bika.lims.interfaces import ISubmitted
from senaite.ast import utils
from senaite.ast.config import BREAKPOINTS_TABLE_KEY
from senaite.ast.config import DISK_CONTENT_KEY
from senaite.ast.config import MIC_KEY
from senaite.ast.config import REPORT_EXTRAPOLATED_KEY
from senaite.ast.config import REPORT_KEY
from senaite.ast.config import RESISTANCE_KEY
from senaite.ast.config import ZONE_SIZE_KEY
from senaite.ast.utils import get_breakpoint
from senaite.ast.utils import get_microorganism
from senaite.ast.utils import get_sensitivity_category
from senaite.ast.utils import get_sensitivity_category_value
from senaite.ast.utils import is_ast_analysis
from senaite.ast.utils import is_interim_empty
from zope.interface import alsoProvides
from zope.interface import noLongerProvides


def calc_ast(analysis_brain_uid, default_return='-'):
    """Handles the calculations of AST-like analyses that are triggered when
    results are saved.
    """
    analysis = api.get_object(analysis_brain_uid)
    if not is_ast_analysis(analysis):
        return default_return

    # Calculate the disk dosages for antibiotics
    calc_disk_dosages(analysis)

    # Calculate the sensitivity categories for antibiotics
    calc_sensitivity_categories(analysis)

    # Calculate sensitivity categories for extrapolated antibiotics
    update_extrapolated_antibiotics(analysis)

    # Update the sensitivity "final" result (for reporting)
    update_sensitivity_result(analysis)

    # The result has been updated already, return it as-it-is
    return analysis.getResult() or default_return


def calc_sensitivity_categories(analysis):
    """Handles the automatic assignment of sensitivity categories (R/I/S) for
    each antibiotic (interim field) assigned to the analysis passed-in.

    The input parameters for the calculation are extracted from analyses
    "Zone diameter (mm)" and "Breakpoints table" from same sample and
    microorganism as the analysis passed-in (siblings).
    """
    keyword = analysis.getKeyword()
    if keyword not in [BREAKPOINTS_TABLE_KEY, ZONE_SIZE_KEY, MIC_KEY]:
        return

    # Get the analysis (keyword: analysis) from same sample and microorganism
    analyses = utils.get_ast_group(analysis)

    # Extract the analysis that stores the sensitivity category
    sensitivity = analyses.get(RESISTANCE_KEY)
    if ISubmitted.providedBy(sensitivity):
        # Sensitivity category submitted already, nothing to do here!
        return None

    # Extract the counterpart analyses
    breakpoints_analysis = analyses.get(BREAKPOINTS_TABLE_KEY)
    target_analysis = analyses.get(ZONE_SIZE_KEY) or analyses.get(MIC_KEY)
    if not all([breakpoints_analysis, target_analysis]):
        return None

    # Get the method used (MIC or Zone size)
    ast_method = target_analysis.getKeyword()

    # The result for each antibiotic is stored as an interim field
    breakpoints = breakpoints_analysis.getInterimFields()
    values = target_analysis.getInterimFields()
    antibiotics = sensitivity.getInterimFields()

    # Get the mapping of Antibiotic -> BreakpointsTable
    breakpoints = dict(map(lambda b: (b['uid'], b['value']), breakpoints))

    # Get the mapping of Antibiotic -> Zone sizes / Antibiotic -> MIC values
    values = dict(map(lambda z: (z['uid'], z['value']), values))

    # Get the microorganism this analysis is associated to
    microorganism = get_microorganism(analysis)

    # Update sensitivity category for each antibiotic
    for antibiotic in antibiotics:
        # Skip non-editable antibiotics
        if not utils.is_interim_editable(antibiotic):
            continue

        # If extrapolated, assume same zone size as representative
        abx_uid = antibiotic.get("primary")
        if not api.is_uid(abx_uid):
            abx_uid = antibiotic["uid"]

        # Get the zone size / MIC value
        value = values.get(abx_uid)
        if not api.is_floatable(value):
            # No value entered yet or not floatable
            continue

        # Get the selected Breakpoints Table for this antibiotic
        breakpoints_uid = breakpoints.get(abx_uid)

        # Get the breakpoint for this microorganism and antibiotic
        breakpoint = get_breakpoint(breakpoints_uid, microorganism, abx_uid)

        # Get the sensitivity category (S|I|R) and choice value
        key = get_sensitivity_category(value, breakpoint, method=ast_method,
                                       default="")
        cat = get_sensitivity_category_value(key, default="")

        # Update the sensitivity category
        antibiotic.update({"value": cat})

    # Assign the antibiotics with the updated sensitivity categories
    sensitivity.setInterimFields(antibiotics)


def calc_disk_dosages(analysis):
    """Handles the automatic assignment of antibiotic dosage for each antibiotic
    (interim field) assigned to the analysis passed-in.

    The antibiotic dosage for each diffusion disk is infered from the
    selected breakpoints table, if any.
    """
    keyword = analysis.getKeyword()
    if keyword not in [BREAKPOINTS_TABLE_KEY]:
        return

    # Get the analysis (keyword: analysis) from same sample and microorganism
    analyses = utils.get_ast_group(analysis)

    # Extract the analyses that store the antibiotic dosage and breakpoints
    disk_dosages_analysis = analyses.get(DISK_CONTENT_KEY)
    breakpoints_analysis = analyses.get(BREAKPOINTS_TABLE_KEY)
    if not all([disk_dosages_analysis, breakpoints_analysis]):
        return None

    # Analysis cannot be updated if submitted
    if ISubmitted.providedBy(disk_dosages_analysis):
        return

    # Get the microorganism this analysis is associated to
    microorganism = get_microorganism(analysis)

    # Get the mapping of Antibiotic -> BreakpointsTable
    breakpoints = breakpoints_analysis.getInterimFields()
    breakpoints = dict(map(lambda b: (b['uid'], b['value']), breakpoints))

    # Dosages are stored as interim fields
    antibiotics = disk_dosages_analysis.getInterimFields()
    for antibiotic in antibiotics:
        # Skip non-editable antibiotics
        if not utils.is_interim_editable(antibiotic):
            continue

        # If extrapolated, assume same zone size as representative
        abx_uid = antibiotic.get("primary")
        if not api.is_uid(abx_uid):
            abx_uid = antibiotic["uid"]

        # Get the selected Breakpoints Table for this category
        breakpoints_uid = breakpoints.get(abx_uid)

        # Get the breakpoint for this microorganism and antibiotic
        breakpoint = get_breakpoint(breakpoints_uid, microorganism, abx_uid)
        if not breakpoint:
            continue

        # Update the dosage
        breakpoint_dosage = breakpoint.get("disk_content")
        if api.to_float(breakpoint_dosage, default=0) > 0:
            antibiotic.update({"value": breakpoint_dosage})

    # Assign the inferred disk dosages
    disk_dosages_analysis.setInterimFields(antibiotics)


def update_extrapolated_antibiotics(analysis):
    """Updates the sensitivity categories (R/I/S) of extrapolated antibiotics
    assigned to the analysis passed-in.

    The sensitivity result (category) obtained for a particular antibiotic is
    extrapolated to extrapolated antibiotics
    """
    keys = [BREAKPOINTS_TABLE_KEY, ZONE_SIZE_KEY, RESISTANCE_KEY, REPORT_KEY]
    if analysis.getKeyword() not in keys:
        return

    def update_extrapolated(target):
        if ISubmitted.providedBy(target):
            return

        # Mapping of UID --> interim field
        interim_fields = target.getInterimFields()
        uids = dict(map(lambda sen: (sen.get("uid"), sen), interim_fields))

        # Iterate over the interim fields and update extrapolated ones
        for interim in interim_fields:
            primary = uids.get(interim.get("primary"))
            if primary:
                interim.update({"value": primary.get("value")})

        target.setInterimFields(interim_fields)

    # Get the analysis (keyword: analysis) from same sample and microorganism
    analyses = utils.get_ast_group(analysis)

    # Update the analysis that stores the zone diameter category
    zone_diameter = analyses.get(ZONE_SIZE_KEY)
    if zone_diameter:
        update_extrapolated(zone_diameter)

    # Update the analysis that stores the sensitivity category
    sensitivity = analyses.get(RESISTANCE_KEY)
    if sensitivity:
        update_extrapolated(sensitivity)

    # Update the analysis that stores the reporting criteria (Y/N)
    reporting = analyses.get(REPORT_KEY)
    if reporting:
        update_extrapolated(reporting)


def update_sensitivity_result(analysis):
    """Updates the sensitivity "final" result of the sensitivity category
    analysis based on the values set to the AST siblings.

    The sensitivity category results for antibiotics of this analysis are stored
    as interim values, while the "final" result of the analysis is a list of
    result options, that is only used for reporting purposes.
    """
    # Get the analysis (keyword: analysis) from same sample and microorganism
    analyses = utils.get_ast_group(analysis)

    # We only do report results from the analysis (Sensitivity) "Category",
    # that are stored as values (R/I/S) for interim fields (antibiotics)
    sensitivity = analyses.get(RESISTANCE_KEY)
    if not sensitivity:
        return

    # Extract the antibiotics (as interim fields) to be reported
    reportable = get_reportable_antibiotics(sensitivity)

    def to_report(option):
        key = option.get("InterimKeyword")
        val = option.get("InterimValue")
        for target in reportable:
            if key == target.get("keyword") and val == target.get("value"):
                return True
        return False

    # Remove the antibiotics to not report from options
    options = sensitivity.getResultOptions()
    options = filter(to_report, options)

    # The final result is a list with result option values
    result = map(lambda o: o.get("ResultValue"), options)

    # No need to keep track of this in audit (this is internal)
    noLongerProvides(sensitivity, IAuditable)

    # Set the final result
    capture_date = sensitivity.getResultCaptureDate()
    sensitivity.setResult(json.dumps(result))
    sensitivity.setResultCaptureDate(capture_date)

    # Re-enable the audit for this analysis
    alsoProvides(sensitivity, IAuditable)


def get_reportable_antibiotics(analysis):
    """Returns the antibiotics to be reported for the ast analysis passed-in
    """
    # Get the analysis (keyword: analysis) from same sample and microorganism
    analyses = utils.get_ast_group(analysis)

    # We only do report results from the analysis (Sensitivity) "Category",
    # that are stored as values (R/I/S) for interim fields (antibiotics)
    sensitivity = analyses.get(RESISTANCE_KEY)
    results = sensitivity.getInterimFields()

    # The analysis "Report Extrapolated" is used to identify the antibiotics
    # their sensitivity category has been extrapolated from representative
    # antibiotics. Build a mapping with keys as the UIDs of the representatives
    # and values as the UIDs of the extrapolated antibiotics to report
    reportable = {}
    extrapolated = analyses.get(REPORT_EXTRAPOLATED_KEY)
    if extrapolated:
        for interim in extrapolated.getInterimFields():
            try:
                selected = json.loads(interim.get("value", "[]"))
            except:
                selected = []
            reportable[interim.get("uid")] = selected

    def is_reportable(interim):
        primary = interim.get("primary", None)
        if primary:
            # Check if the primary is reportable
            uid = interim.get("uid")
            return uid in reportable.get(primary, [])
        return interim.get("value") == "1"

    # The analysis "Report" is used to identify results from the sensitivity
    # category analysis that need to be reported
    report = analyses.get(REPORT_KEY)
    if report:
        # The results to be reported are defined by the Y/N values
        # XXX senaite.app.listing has no support bool type for interim fields
        report_values = report.getInterimFields()
        to_report = filter(is_reportable, report_values)

        # Get the abbreviation of antibiotics (keyword)
        antibiotics = map(lambda k: k.get("keyword"), to_report)

        # Bail out (Sensitivity) "Category" results to not report
        results = filter(lambda r: r.get("keyword") in antibiotics, results)

    # Only report those with result set
    return filter(lambda res: not is_interim_empty(res), results)
