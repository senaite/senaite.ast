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
import itertools
import json

from bika.lims import api
from bika.lims import workflow as wf
from bika.lims.catalog import SETUP_CATALOG
from bika.lims.interfaces import IInternalUse
from bika.lims.interfaces import ISubmitted
from bika.lims.interfaces import IVerified
from bika.lims.utils.analysis import create_analysis
from bika.lims.workflow import doActionFor
from senaite.ast import logger
from senaite.ast import messageFactory as _
from senaite.ast.config import BREAKPOINTS_TABLE_KEY
from senaite.ast.config import IDENTIFICATION_KEY
from senaite.ast.config import RESISTANCE_KEY
from senaite.ast.config import SERVICES_SETTINGS
from senaite.ast.interfaces import IASTAnalysis
from zope.interface import alsoProvides

_marker = object()


def get_service(keyword, default=_marker):
    """Returns the Analysis Service for the given keyword, if any
    """
    query = {
        "portal_type": "AnalysisService",
        "getKeyword": keyword
    }
    brains = api.search(query, SETUP_CATALOG)
    if len(brains) == 1:
        return api.get_object(brains[0])
    elif default is _marker:
        raise KeyError("No service found for '{}'".format(keyword))
    return default


def new_analysis_id(sample, analysis_keyword):
    """Returns a new analysis id for an eventual new test with given keyword
    to prevent clashes with ids of other analyses from same sample
    """
    analyses = sample.getAnalyses(getKeyword=analysis_keyword)
    existing_ids = map(api.get_id, analyses)
    idx = len(analyses)
    while True:
        new_id = "{}-{}".format(analysis_keyword, idx)
        if new_id not in existing_ids:
            return new_id
        idx += 1


def create_ast_analyses(sample, keywords, microorganism, antibiotics):
    """Create new AST analyses
    """
    output = []
    for keyword in keywords:
        an = create_ast_analysis(sample, keyword, microorganism, antibiotics)
        output.append(an)
    return output


def create_ast_analysis(sample, keyword, microorganism, antibiotics):
    """Creates a new AST analysis
    """
    # Convert antibiotics to interim fields
    interim_fields = map(lambda ab: to_interim(keyword, ab), antibiotics)

    # Create a new ID to prevent clashes
    new_id = new_analysis_id(sample, keyword)

    # Create the analysis
    service = get_service(keyword)
    analysis = create_analysis(sample, service, id=new_id)

    # Assign the name of the microorganism as the title
    title = get_analysis_title(keyword, microorganism)
    short_title = api.get_title(microorganism)
    analysis.setTitle(title)
    analysis.setShortTitle(short_title)

    # Assign the antibiotics as interim fields
    analysis.setInterimFields(interim_fields)

    # Compute all combinations of interim/antibiotic and possible result and
    # and generate the result options for this analysis (the "Result" field is
    # never displayed and is only used for reporting)
    result_options = get_result_options(analysis)
    analysis.setResultOptions(result_options)

    if keyword == BREAKPOINTS_TABLE_KEY:
        # This is a breakpoints analysis, we need to populate the interim
        # choices dynamically
        update_breakpoint_tables_choices(analysis)

    # Apply the IASTAnalysis and IInternalUser marker interfaces
    alsoProvides(analysis, IASTAnalysis)
    alsoProvides(analysis, IInternalUse)

    # Initialize the analysis and reindex
    doActionFor(analysis, "initialize")
    analysis.reindexObject()

    return analysis


def update_ast_analysis(analysis, antibiotics, remove=False):
    # There is nothing to do if the analysis has been verified
    analysis = api.get_object(analysis)
    if IVerified.providedBy(analysis):
        return

    # Convert antibiotics to interim fields
    keyword = analysis.getKeyword()
    interim_fields = map(lambda ab: to_interim(keyword, ab), antibiotics)

    # Get the analysis interim fields
    an_interims = copy.deepcopy(analysis.getInterimFields()) or []
    an_keys = sorted(map(lambda i: i.get("keyword"), an_interims))

    # Remove non-specified antibiotics
    if remove:
        in_keys = map(lambda i: i.get("keyword"), interim_fields)
        an_interims = filter(lambda a: a["keyword"] in in_keys, an_interims)

    # Keep analysis' original antibiotics
    abx = filter(lambda a: a["keyword"] not in an_keys, interim_fields)
    an_interims.extend(abx)

    # Is there any difference?
    new_keys = sorted(map(lambda i: i.get("keyword"), an_interims))
    if new_keys == an_keys:
        # No changes
        return

    # If no antibiotics, remove the analysis
    if remove and not an_interims:
        sample = analysis.getRequest()
        sample._delObject(api.get_id(analysis))
        return

    if ISubmitted.providedBy(analysis):
        # Analysis has been submitted already, retract
        succeed, message = wf.doActionFor(analysis, "retract")
        if not succeed:
            path = api.get_path(analysis)
            logger.error("Cannot retract analysis '{}'".format(path))
            return

    # Assign the antibiotics
    analysis.setInterimFields(an_interims)

    # Update the antibiotics with the proper choices if necessary
    if keyword == BREAKPOINTS_TABLE_KEY:
        update_breakpoint_tables_choices(analysis)

    # Compute all combinations of interim/antibiotic and possible result and
    # and generate the result options for this analysis (the "Result" field is
    # never displayed and is only used for reporting)
    result_options = get_result_options(analysis)
    analysis.setResultOptions(result_options)

    # Apply the IASTAnalysis marker interface (just in case)
    alsoProvides(analysis, IASTAnalysis)

    analysis.reindexObject()


def update_breakpoint_tables_choices(analysis, default_table=None):
    """Updates the choices option for each interim field from the passed-in
    analysis, that represents an antibiotic, with the list of breakpoints
    tables that better suit with the microorganism the analysis is associated
    to and with the antibiotic
    """
    default_table = default_table or "0"
    microorganism = get_microorganism(analysis)
    interim_fields = analysis.getInterimFields()
    for interim_field in interim_fields:

        # Get the breakpoint tables for this antibiotic and microorganism
        uid = interim_field.get("uid")
        breakpoints = get_breakpoints_tables_for(microorganism, uid)
        breakpoints_uids = map(api.get_uid, breakpoints)

        # Convert these breakpoints to interim choices and update interim
        choices = to_interim_choices(breakpoints, empty_value=_("N/S"))
        interim_field.update({"choices": choices})

        # Set the default breakpoints table, if match
        value = interim_field.get("value", default_table)
        if value in breakpoints_uids:
            interim_field.update({"value": value})
        else:
            interim_field.update({"value": default_table})

    analysis.setInterimFields(interim_fields)

    # Set the default result to '-' so user can directly save without the
    # need of manually confirming each interim field value on result entry
    analysis.setResult("-")


def to_interim(keyword, antibiotic):
    """Returns the interim field settings for the antibiotic and service
    keyword passed-in
    """
    if isinstance(antibiotic, dict):
        # Already an interim
        return antibiotic

    properties = SERVICES_SETTINGS[keyword]
    obj = api.get_object(antibiotic)
    return {
        "keyword": obj.abbreviation,
        "title": obj.abbreviation,
        "choices": properties.get("choices", ""),
        "value": "",
        "unit": "",
        "wide": False,
        "hidden": False,
        "size": properties.get("size", "5"),
        "type": properties.get("type", ""),
        "full_title": api.get_title(obj),
        "uid": api.get_uid(obj),
    }


def get_result_options(analysis):
    """Generates a list of result option from the analysis passed in, where
    each result option represents a combination of interim/antibiotic and
    possible result
    """
    def to_result_option(interim_field, interim_choice, result_value):
        value = None

        # Abbreviation and full name of antibiotic
        abbreviation = interim_field.get("keyword")
        full_name = interim_field.get("full_title")

        text = interim_choice.split(":")
        if len(text) > 1:
            result_text = "{}: {}".format(full_name, text[1].strip())
            value = {
                "ResultText": result_text,
                "ResultValue": result_value,
                "InterimKeyword": abbreviation,
                "InterimValue": text[0],
            }
        return value

    options = []
    for interim in analysis.getInterimFields():
        choices = interim.get("choices")
        if not choices:
            continue

        # Generate the result options
        for choice in choices.split("|"):
            val = str(len(options))
            option = to_result_option(interim, choice, val)
            if option:
                options.append(option)

    return options


def get_analysis_title(keyword, microorganism):
    """Returns the analysis title for the service keyword and microorganism
    """
    title = SERVICES_SETTINGS[keyword]["title"]
    obj = api.get_object(microorganism)
    return title.format(api.get_title(obj))


def get_ast_analyses(sample, short_title=None, skip_invalid=True):
    """Returns the ast analyses assigned to the sample passed in and for the
    microorganism name specified, if any
    """
    analyses = sample.getAnalyses(getPointOfCapture="ast")
    analyses = map(api.get_object, analyses)

    if short_title:
        # Filter by microorganism name (short title)
        analyses = filter(lambda a: a.getShortTitle() == short_title, analyses)

    # Skip invalid analyses
    skip = skip_invalid and ["cancelled", "retracted", "rejected"] or []
    analyses = filter(lambda a: api.get_review_status(a) not in skip, analyses)

    return analyses


def get_ast_siblings(analysis):
    """Returns the AST analyses for same sample and microorganism
    """
    sample = analysis.getRequest()
    microorganism = analysis.getShortTitle()
    analyses = get_ast_analyses(sample, short_title=microorganism)
    return filter(lambda an: an != analysis, analyses)


def get_identified_microorganisms(sample):
    """Returns the identified microorganisms from the sample passed-in. It
    resolves the microorganisms by looking to the results of the
    "Identification" analysis
    """
    keyword = IDENTIFICATION_KEY
    ans = sample.getAnalyses(getKeyword=keyword, full_objects=True)

    # Discard invalid analyses
    skip = ["rejected", "cancelled", "retracted"]
    ans = filter(lambda a: api.get_review_status(a) not in skip, ans)

    # Get the names of the selected microorganisms
    names = map(get_microorganisms_from_result, ans)
    names = list(itertools.chain.from_iterable(names))

    # Get the microorganisms
    objects = api.get_setup().microorganisms.objectValues()
    return filter(lambda m: api.get_title(m) in names, objects)


def get_microorganism(analysis):
    """Returns the microorganism object from the analysis passed-in, if any
    """
    microorganism = get_microorganisms([analysis, ])
    return microorganism and microorganism[0] or None


def get_microorganisms(analyses):
    """Returns the list of microorganisms from the analyses passed-in
    """
    names = map(lambda a: a.getShortTitle(), analyses)
    objects = api.get_setup().microorganisms.objectValues()
    objects = filter(lambda m: api.get_title(m) in names, objects)
    return filter(None, objects)


def get_antibiotics(analyses, uids_only=False):
    """Returns the list of antibiotics assigned to the analyses passed-in
    """
    if isinstance(analyses, (list, tuple)):
        uids = map(lambda an: get_antibiotics(an, uids_only=True), analyses)
        uids = list(itertools.chain.from_iterable(uids))
        # Remove duplicates and Nones
        uids = filter(None, list(set(uids)))
    else:
        # Antibiotics are stored as interim fields
        analysis = api.get_object(analyses)
        interim_fields = analysis.getInterimFields()
        uids = map(lambda i: i.get("uid"), interim_fields)
        uids = filter(None, uids)

    if not uids:
        return []

    if uids_only:
        return uids

    query = {"UID": uids, "portal_type": "Antibiotic"}
    brains = api.search(query, SETUP_CATALOG)
    return map(api.get_object, brains)


def get_microorganisms_from_result(analysis):
    """Returns the microorganisms from the Identification analysis passed-in
    """
    if analysis.getKeyword() != IDENTIFICATION_KEY:
        return []

    try:
        selected = json.loads(analysis.getResult())
        selected = map(str, selected)
    except Exception as e:
        logger.error("Cannot extract microorganisms from {}: {}".format(
            api.get_path(analysis), str(e)
        ))
        return []

    options = analysis.getResultOptions()
    options = filter(lambda o: str(o["ResultValue"]) in selected, options)
    names = map(lambda o: o["ResultText"], options)
    return filter(None, names)


def get_panels_for(microorganisms):
    """Returns a list of active AST Panels, sorted by title ascending, that at
    least have one of the microorganisms passed-in assigned
    """
    output = []
    uids = map(api.get_uid, microorganisms)
    query = {
        "portal_type": "ASTPanel",
        "sort_on": "sortable_title",
        "sort_order": "ascending",
        "is_active": True,
    }
    panels = map(api.get_object, api.search(query, SETUP_CATALOG))
    for panel in panels:
        matches = map(lambda p: p in uids, panel.microorganisms)
        if any(matches):
            output.append(panel)
    return output


def get_breakpoints_tables_for(microorganism, antibiotic):
    """Returns the list of BreakpointsTable objects registered and active that
    have an entry for the microorganism and antibiotic passed-in
    """
    query = {
        "portal_type": "BreakpointsTable",
        "sort_on": "sortable_title",
        "sort_order": "ascending",
        "is_active": True,
    }
    matches = []
    for brain in api.search(query, SETUP_CATALOG):
        obj = api.get_object(brain)
        breakpoint = get_breakpoint(obj, microorganism, antibiotic)
        if breakpoint:
            matches.append(obj)

    return matches


def to_interim_choices(objects, empty_value=None):
    """Returns a string with a suitable format for its use as choices subfield
    for interim fields
    """
    choices = []
    if empty_value:
        choices.append("0:{}".format(empty_value))

    for obj in objects:
        obj = api.get_object(obj)
        uid = api.get_uid(obj)
        title = api.get_title(obj)
        choice = "{}:{}".format(uid, title)
        choices.append(choice)
    return "|".join(choices)


def get_breakpoint(breakpoints_table, microorganism, antibiotic):
    """Returns the breakpoint from the breakpoints_table for the antibiotic and
    microorganism specified if exists. Returns empty dict otherwise
    """
    if not all([breakpoints_table, microorganism, antibiotic]):
        return {}

    if breakpoints_table == "0":
        # Default N/A breakpoint
        return {}

    break_obj = api.get_object(breakpoints_table, default=None)
    if not break_obj:
        return {}

    # Find out first if the antibiotic is set
    antibiotic_uid = api.get_uid(antibiotic)
    breakpoints = filter(lambda v: antibiotic_uid == v.get("antibiotic"),
                         break_obj.breakpoints)
    if not breakpoints:
        return {}

    microorganism_uid = api.get_uid(microorganism)
    for val in breakpoints:
        if val.get("microorganism") == microorganism_uid:
            return copy.deepcopy(val)

    # Breakpoints table can either map to microorganism or category, but
    # breakpoint for microorganism always have priority over the breakpoint set
    # for the category the microorganism belongs to
    microorganism = api.get_object(microorganism)
    category_uid = microorganism.category and microorganism.category[0] or ""
    for val in break_obj.breakpoints:
        if val.get("microorganism") == category_uid:
            return copy.deepcopy(val)

    return {}


def get_non_ast_points_of_capture():
    """Extract the points of capture assigned to services registered in the
    system. If no services registered, returns a list with default poc "lab"
    """
    catalog = api.get_tool(SETUP_CATALOG)
    pocs = catalog.Indexes["point_of_capture"].uniqueValues()
    pocs = filter(lambda poc: poc != "ast", pocs)
    if not pocs:
        pocs = ["lab"]
    return pocs


def get_sensitivity_category(zone_size, breakpoint, default=_marker):
    """Returns the sensitivity category inferred from the zone_size and
    breakpoint passed-in. Returns default value if zone size is negative and/or
    breakpoint is None
    """
    if not breakpoint:
        if default is _marker:
            raise ValueError("Breakpoint is missing")
        return default

    zone_size = api.to_float(zone_size, -1)
    if zone_size < 0:
        # zero and non-positive zone_sizes are not possible
        if default is _marker:
            raise ValueError("Zone size is not valid")
        return default

    diameter_r = api.to_float(breakpoint.get("diameter_r"))
    if zone_size < diameter_r:
        # R: resistant
        return "R"

    diameter_s = api.to_float(breakpoint.get("diameter_s"))
    if zone_size >= diameter_s:
        # S: sensible
        return "S"

    # I: Susceptible at increased exposure
    return "I"


def get_sensitivity_category_value(text, default=_marker):
    """Returns the choice value defined in the Sensitivity Category service for
    the option text passed-in
    """
    # Resistance test (category) pre-defined choices
    choices = SERVICES_SETTINGS[RESISTANCE_KEY]["choices"]
    choices = map(lambda choice: choice.split(":"), choices.split("|"))
    choices = dict(map(lambda choice: (choice[1], choice[0]), choices))
    value = choices.get(text, None)
    if value is None:
        if default is _marker:
            raise ValueError("Sensitivity category is not valid")
        return default
    return value
