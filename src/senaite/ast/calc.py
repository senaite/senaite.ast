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
from bika.lims.interfaces import ISubmitted
from senaite.ast import utils
from senaite.ast.config import BREAKPOINTS_TABLE_KEY
from senaite.ast.config import DISK_CONTENT_KEY
from senaite.ast.config import RESISTANCE_KEY
from senaite.ast.config import ZONE_SIZE_KEY
from senaite.ast.utils import get_breakpoint
from senaite.ast.utils import get_microorganism
from senaite.ast.utils import get_sensitivity_category
from senaite.ast.utils import get_sensitivity_category_value


def calc_sensitivity_category(analysis_brain_uid, default_return='-'):
    """Handles the automatic assignment of the result for the sensitivity
    testing category analysis (ast_resistance) based on the value set for both
    the diameter zone in mm and the breakpoints table, if any.
    """
    analysis = api.get_object(analysis_brain_uid)
    keyword = analysis.getKeyword()
    if keyword not in [BREAKPOINTS_TABLE_KEY, ZONE_SIZE_KEY]:
        return

    def get_by_keyword(analyses_in, service_keyword):
        for an in analyses_in:
            if an.getKeyword() == service_keyword:
                return an
        return None

    # Get the AST siblings for same sample and microorganism
    siblings = utils.get_ast_siblings(analysis)
    analyses = siblings + [analysis]

    # Extract the analysis that stores the sensitivity category
    resistance_analysis = get_by_keyword(analyses, RESISTANCE_KEY)
    if ISubmitted.providedBy(resistance_analysis):
        # Sensitivity category submitted already, nothing to do here!
        return default_return

    # Extract the counterpart analyses
    breakpoints_analysis = get_by_keyword(analyses, BREAKPOINTS_TABLE_KEY)
    zone_sizes_analysis = get_by_keyword(analyses, ZONE_SIZE_KEY)
    if not all([breakpoints_analysis, zone_sizes_analysis]):
        return default_return

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
        value = get_sensitivity_category_value(key, default=None)
        if not category:
            continue

        # Update the sensitivity category
        category.update({"value": value})

    # Assign the updated categories to the resistance analysis
    resistance_analysis.setInterimFields(categories)

    # Validate if all values for categories interims are set
    valid = map(lambda cat: cat.get("value"), categories)
    if all(valid):
        # Let's set the result as '-' so user can directly submit the whole
        # analysis without the need of confirming every single one
        resistance_analysis.setResult("-")

    # Update disk dosage / concentration
    disk_dosages_analysis = get_by_keyword(analyses, DISK_CONTENT_KEY)
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

    # Return something, cause is called by a Calculation
    return default_return
