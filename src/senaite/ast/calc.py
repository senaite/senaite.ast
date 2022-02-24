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
# Copyright 2020-2021 by it's authors.
# Some rights reserved, see README and LICENSE.

from bika.lims import api
from bika.lims.interfaces import IAuditable
from bika.lims.interfaces import ISubmitted
from senaite.ast import utils
from senaite.ast.config import BREAKPOINTS_TABLE_KEY
from senaite.ast.config import DISK_CONTENT_KEY
from senaite.ast.config import REPORT_KEY
from senaite.ast.config import RESISTANCE_KEY
from senaite.ast.config import ZONE_SIZE_KEY
from senaite.ast.utils import get_breakpoint
from senaite.ast.utils import get_microorganism
from senaite.ast.utils import get_sensitivity_category
from senaite.ast.utils import get_sensitivity_category_value
from senaite.ast.utils import is_ast_analysis
from zope.interface import alsoProvides
from zope.interface import noLongerProvides


def calc_ast(analysis_brain_uid, default_return='-'):
    """Handles the calculations of AST-like analyses that are triggered when
    results are saved.
    """
    analysis = api.get_object(analysis_brain_uid)
    if not is_ast_analysis(analysis):
        return default_return

    import pdb;pdb.set_trace()

    # Calculate the sensitivity categories for antibiotics
    calc_sensitivity_categories(analysis)

    # Update the sensitivity "final" result (for reporting)
    update_sensitivity_result(analysis)

    return default_return


def calc_sensitivity_categories(analysis):
    """Handles the automatic assignment of sensitivity categories (R/I/S) for
    each antibiotic (interim field) assigned to the analysis passed-in.

    The input parameters for the calculation are extracted from analyses
    "Zone diameter (mm)" and "Breakpoints table" from same sample and
    microorganism as the analysis passed-in (siblings).
    """
    keyword = analysis.getKeyword()
    if keyword not in [BREAKPOINTS_TABLE_KEY, ZONE_SIZE_KEY]:
        return

    # Get the AST siblings for same sample and microorganism
    analyses = utils.get_ast_siblings(analysis) + [analysis]
    keywords = map(lambda an: an.getKeyword(), analyses)
    analyses = dict(zip(keywords, analyses))

    # Extract the analysis that stores the sensitivity category
    sensitivity = analyses.get(RESISTANCE_KEY)
    if ISubmitted.providedBy(sensitivity):
        # Sensitivity category submitted already, nothing to do here!
        return None

    # Extract the counterpart analyses
    breakpoints_analysis = analyses.get(BREAKPOINTS_TABLE_KEY)
    zone_sizes_analysis = analyses.get(ZONE_SIZE_KEY)
    if not all([breakpoints_analysis, zone_sizes_analysis]):
        return None

    # The result for each antibiotic is stored as an interim field
    breakpoints = breakpoints_analysis.getInterimFields()
    zone_sizes = zone_sizes_analysis.getInterimFields()
    categories = sensitivity.getInterimFields()

    # Get the mapping of Antibiotic -> BreakpointsTable
    breakpoints = dict(map(lambda b: (b['uid'], b['value']), breakpoints))

    # Get the mapping of Antibiotic -> Zone sizes
    zone_sizes = dict(map(lambda z: (z['uid'], z['value']), zone_sizes))

    # Get the microorganism this analysis is associated to
    microorganism = get_microorganism(analysis)

    # Update sensitivity categories
    for category in categories:
        abx_uid = category["uid"]

        # Get the zone size
        zone_size = zone_sizes.get(abx_uid)
        if not api.is_floatable(zone_size):
            # No zone size entered yet or not floatable
            continue

        # Get the selected Breakpoints Table for this category
        breakpoints_uid = breakpoints.get(abx_uid)

        # Get the breakpoint for this microorganism and antibiotic
        breakpoint = get_breakpoint(breakpoints_uid, microorganism, abx_uid)

        # Get the sensitivity category (S|I|R) and choice value
        key = get_sensitivity_category(zone_size, breakpoint, default="")
        value = get_sensitivity_category_value(key, default="")

        # Update the sensitivity category
        category.update({"value": value})

    # Assign the updated categories to the sensitivity category analysis
    sensitivity.setInterimFields(categories)

    # Update disk dosage / concentration
    disk_dosages_analysis = analyses.get(DISK_CONTENT_KEY)
    if disk_dosages_analysis:
        disk_dosages = disk_dosages_analysis.getInterimFields()

        for dosage in disk_dosages:
            abx_uid = dosage["uid"]

            # Get the selected Breakpoints Table for this category
            breakpoints_uid = breakpoints.get(abx_uid)

            # Get the breakpoint for this microorganism and antibiotic
            breakpoint = get_breakpoint(breakpoints_uid, microorganism, abx_uid)
            if not breakpoint:
                continue

            # Update the dosage
            breakpoint_dosage = breakpoint.get("disk_content")
            if api.to_float(breakpoint_dosage, default=0) > 0:
                dosage.update({"value": breakpoint_dosage})

        # Assign the inferred disk dosages
        disk_dosages_analysis.setInterimFields(disk_dosages)

        # Validate if all values for dosage interims are set
        valid = map(lambda cat: cat.get("value"), categories)
        if all(valid):
            # Let's set the result as '-' so user can directly submit the whole
            # analysis without the need of confirming every single one
            disk_dosages_analysis.setResult("-")


def update_sensitivity_result(analysis):
    """Updates the sensitivity "final" result of the sensitivity category
    analysis based on the values set to the AST siblings.

    The sensitivity category results for antibiotics of this analysis are stored
    as interim values, while the "final" result of the analysis is a list of
    result options, that is only used for reporting purposes.
    """
    analyses = utils.get_ast_siblings(analysis) + [analysis]
    keywords = map(lambda an: an.getKeyword(), analyses)
    analyses = dict(zip(keywords, analyses))

    # We only do report results from the analysis (Sensitivity) "Category",
    # that are stored as values (R/I/S) for interim fields (antibiotics)
    sensitivity = analyses.get(RESISTANCE_KEY)
    results = sensitivity.getInterimFields()

    # The analysis "Report" is used to identify the results from the sensitivity
    # category analysis that need to be reported
    report = analyses.get(REPORT_KEY)
    if report:
        # The results to be reported are defined by the Y/N values
        # XXX senaite.app.listing has no support boolean type for interim fields
        to_report = report.getInterimFields()
        to_report = filter(lambda k: k.get("value") == "1", to_report)

        # Get the abbreviation of microorganisms (keyword)
        keywords = map(lambda k: k.get("keyword"), to_report)

        # Bail out (Sensitivity) "Category" results to not report
        results = filter(lambda r: r.get("keyword") in keywords, results)

    def to_report(option):
        key = option.get("InterimKeyword")
        val = option.get("InterimValue")
        for target in results:
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
    sensitivity.setResult(result)
    sensitivity.setResultCaptureDate(capture_date)

    # Re-enable the audit for this analysis
    alsoProvides(sensitivity, IAuditable)
