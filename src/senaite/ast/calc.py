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
from senaite.ast.config import RESISTANCE_KEY
from senaite.ast.config import ZONE_SIZE_KEY
from senaite.ast.utils import get_microorganism


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

    # Extract the counterpart analysis
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

        # Find-out the category by looking to the breakpoints table
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

    # Assign the updated categories to the resistance analysis
    resistance_analysis.setInterimFields(categories)

    # Validate if all values for categories interims are set
    valid = map(lambda cat: cat.get("value"), categories)
    if all(valid):
        # Let's set the result as '-' so user can directly submit the whole
        # analysis without the need of confirming every single one
        resistance_analysis.setResult("-")

    # Return something, cause is called by a Calculation
    return default_return
