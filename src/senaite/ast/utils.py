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

import copy

import collections
import itertools
import json
from bika.lims import api
from bika.lims.catalog import SETUP_CATALOG
from bika.lims.interfaces import IInternalUse
from bika.lims.interfaces import ISubmitted
from bika.lims.interfaces import IVerified
from bika.lims.utils import changeWorkflowState
from bika.lims.utils.analysis import create_analysis
from bika.lims.workflow import doActionFor
from senaite.ast import logger
from senaite.ast import messageFactory as _
from senaite.ast.config import AST_POINT_OF_CAPTURE
from senaite.ast.config import BREAKPOINTS_TABLE_KEY
from senaite.ast.config import IDENTIFICATION_KEY
from senaite.ast.config import MIC_KEY
from senaite.ast.config import REPORT_EXTRAPOLATED_KEY
from senaite.ast.config import REPORT_KEY
from senaite.ast.config import RESISTANCE_KEY
from senaite.ast.config import SERVICES_SETTINGS
from senaite.ast.config import ZONE_SIZE_KEY
from senaite.ast.interfaces import IASTAnalysis
from senaite.core.p3compat import cmp
from senaite.core.workflow import ANALYSIS_WORKFLOW
from zope.interface import alsoProvides
from zope.interface import noLongerProvides

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

    # Apply the interface markers
    alsoProvides(analysis, IASTAnalysis)

    # Don't display AST analyses in report except Sensitivity one
    if keyword not in [RESISTANCE_KEY]:
        alsoProvides(analysis, IInternalUse)

    # Delegate the assignment of antibiotics
    update_ast_analysis(analysis, antibiotics)

    # Initialize the analysis and reindex
    doActionFor(analysis, "initialize")
    analysis.reindexObject()

    # Set the default result to '-' so user can directly save without the
    # need of manually confirming each interim field value on result entry
    analysis.setResult("-")
    analysis.setResultCaptureDate(None)

    return analysis


def set_antibiotics(analysis, antibiotics, purge=False):
    """Assigns the specified antibiotics from the AST-like analysis passed-in
    """
    def get_uid(antibiotic):
        if api.is_uid(antibiotic):
            return antibiotic
        elif api.is_object(antibiotic):
            return api.get_uid(antibiotic)
        elif isinstance(antibiotic, dict):
            return get_uid(antibiotic.get("uid"))
        return None

    # Extract the antibiotic uids
    uids = filter(None, map(get_uid, antibiotics))

    # Extract the interim fields (antibiotics) from the analysis
    interim_fields = copy.deepcopy(analysis.getInterimFields()) or []
    if purge:
        interim_fields = filter(lambda i: i["uid"] in uids, interim_fields)

    # Extend with the antibiotics that are missing
    keyword = analysis.getKeyword()
    present_uids = filter(None, map(get_uid, interim_fields))
    missing_uids = filter(lambda i: i not in present_uids, uids)
    missing_interims = map(lambda ab: to_interim(keyword, ab), missing_uids)
    interim_fields.extend(missing_interims)
    analysis.setInterimFields(interim_fields)


def update_ast_analysis(analysis, antibiotics, purge=False):
    """Updates the AST-like Analysis with the antibiotics passed-in.
    Non-specified antibiotics will be purged from the analysis if purge
    parameter is True
    """
    # There is nothing to do if the analysis has been verified
    analysis = api.get_object(analysis)
    if IVerified.providedBy(analysis):
        return

    # Re-sort antibiotics passed-in to follow same order as the original ones
    original = get_antibiotics(analysis, uids_only=True)

    def sort_antibiotics(a, b):
        def get_idx(abx):
            uid = api.get_uid(abx)
            return original.index(uid) if uid in original else len(original)
        return cmp(get_idx(a), get_idx(b))

    antibiotics = sorted(antibiotics, cmp=sort_antibiotics)

    # Re-assign the antibiotics
    set_antibiotics(analysis, antibiotics, purge=purge)

    # If no antibiotics, remove the analysis
    interim_fields = copy.deepcopy(analysis.getInterimFields()) or []
    if purge and not interim_fields:
        sample = analysis.getRequest()
        sample._delObject(api.get_id(analysis))
        return

    # Extend with extrapolated antibiotics
    keyword = analysis.getKeyword()
    if keyword in [RESISTANCE_KEY, REPORT_KEY]:
        extrapolated = get_extrapolated_interims(antibiotics, keyword)
        interim_fields.extend(extrapolated)
        analysis.setInterimFields(interim_fields)

    # Update the antibiotics with the proper choices if necessary
    if keyword == BREAKPOINTS_TABLE_KEY:
        update_breakpoint_tables_choices(analysis)

    # Update the choices for selective reporting of extrapolated antibiotics
    if keyword == REPORT_EXTRAPOLATED_KEY:
        update_extrapolated_reporting(analysis)

    # Compute all combinations of interim/antibiotic and possible result and
    # and generate the result options for this analysis (the "Result" field is
    # never displayed and is only used for reporting)
    result_options = get_result_options(analysis)
    analysis.setResultOptions(result_options)

    # Try to rollback
    if IVerified.providedBy(analysis):
        noLongerProvides(analysis, IVerified)

    if ISubmitted.providedBy(analysis):
        noLongerProvides(analysis, ISubmitted)
        get_prev_status = api.get_previous_worfklow_status_of
        to_skip = ["to_be_verified", "verified"]
        prev_status = get_prev_status(analysis, skip=to_skip)
        changeWorkflowState(analysis, ANALYSIS_WORKFLOW, prev_status)

    # If the sample is in to_be_verified status, try to rollback
    sample = analysis.getRequest()
    doActionFor(sample, "rollback")

    # Reindex the object
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


def update_extrapolated_reporting(analysis):
    """Updates the interim results options of the analysis that stores the
    selective reporting of extrapolated antibiotics. The function updates the
    extrapolated antibiotics for selection in the analysis for selective
    reporting based on the representative antibiotics set
    """
    interim_fields = copy.deepcopy(analysis.getInterimFields()) or []
    new_interim_fields = []
    for interim in interim_fields:
        antibiotic = api.get_object(interim["uid"])
        extrapolated = get_extrapolated_antibiotics(antibiotic)
        if not extrapolated:
            continue

        # Generate the choices list
        choices = []
        for extra in extrapolated:
            choice = "{}:{}".format(api.get_uid(extra), extra.abbreviation)
            choices.append(choice)

        interim.update({
            "choices": "|".join(choices),
            "result_type": "multichoice",
        })
        new_interim_fields.append(interim)

    # Re-assign the interim fields
    analysis.setInterimFields(new_interim_fields)


def to_interim(keyword, antibiotic, **kwargs):
    """Returns the interim field settings for the antibiotic and service
    keyword passed-in
    """
    if isinstance(antibiotic, dict):
        # Already an interim
        return antibiotic

    properties = SERVICES_SETTINGS[keyword]
    obj = api.get_object(antibiotic)
    interim_field = {
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
    interim_field.update(kwargs)
    return interim_field


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
        if len(text) > 0:
            interim_value = text[0]
            result_text = len(text) > 1 and text[1].strip() or ""
            result_text = "{}: {}".format(full_name, result_text)
            value = {
                "ResultText": result_text,
                "ResultValue": result_value,
                "InterimKeyword": abbreviation,
                "InterimValue": interim_value,
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
    analyses = sample.getAnalyses(getPointOfCapture=AST_POINT_OF_CAPTURE)
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


def get_ast_group(analysis):
    """Returns a dict with the active ast analysis from same sample and
    for same microorganism as the analysis passed-in. The dict key is the
    keyword of the analysis and value is the analysis
    """
    analyses = get_ast_siblings(analysis) + [analysis]
    keywords = map(lambda an: an.getKeyword(), analyses)
    return dict(zip(keywords, analyses))


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


def get_antibiotics(analyses, uids_only=False, filter_criteria=None):
    """Returns the list of antibiotics assigned to the analyses passed-in

    :param analyses: analysis or analyses to look assigned antibiotics
    :type analyses: list of or single analysis brain, uid or object
    :param uids_only: whether if only uids have to be returned
    :type uids_only: bool
    :param filter_criteria: function to filter analysis interims by
    :type filter_criteria: function that accepts a dict as a parameter
    :returns: list of antibiotic uids or objects
    :rtype: list
    """
    if isinstance(analyses, (list, tuple)):
        uids = []
        for an in analyses:
            abx = get_antibiotics(an, uids_only=True,
                                  filter_criteria=filter_criteria)
            uids.extend(abx)
        uids = list(collections.OrderedDict.fromkeys(uids))
    else:
        # Antibiotics are stored as interim fields
        analysis = api.get_object(analyses)
        uids = []
        for interim in analysis.getInterimFields():
            abx_uid = interim.get("uid")
            if filter_criteria and callable(filter_criteria):
                if not filter_criteria(interim):
                    continue
            uids.append(abx_uid)

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

    # Look for the breakpoint for this specific microorganism
    microorganism_uid = api.get_uid(microorganism)
    for val in breakpoints:
        if val.get("microorganism") == microorganism_uid:
            return copy.deepcopy(val)

    # Look for the breakpoint for the category this microorganism belongs to
    microorganism = api.get_object(microorganism)
    category_uid = microorganism.category and microorganism.category[0] or ""
    for val in breakpoints:
        if val.get("microorganism") == category_uid:
            return copy.deepcopy(val)

    return {}


def get_non_ast_points_of_capture():
    """Extract the points of capture assigned to services registered in the
    system. If no services registered, returns a list with default poc "lab"
    """
    catalog = api.get_tool(SETUP_CATALOG)
    pocs = catalog.Indexes["point_of_capture"].uniqueValues()
    pocs = filter(lambda poc: poc != AST_POINT_OF_CAPTURE, pocs)
    if not pocs:
        pocs = ["lab"]
    return pocs


def get_sensitivity_category(value, breakpoint, method, default=_marker):
    """Returns the sensitivity category inferred from the zone_size or MIC
    value and the breakpoint passed-in. Returns default value if zone size is
    negative and/or breakpoint is None

    :param value: size in mm of the antibiotic inhibition zone or MIC value
    :param breakpoint: breakpoint that defines the sensitivity categories
        depending on the microorganism, antibiotic, potency and zone size
    :param method: the id of the method (service keyword) that refers to
        MIC value or Zone size
    :type value: string, float, int
    :type breakpoint: dict
    :type method: string or analysis
    :returns: the standard EUCAST sensitivity category (R, S or I)
    :rtype: string
    """
    if not breakpoint:
        if default is _marker:
            raise ValueError("Breakpoint is missing")
        return default

    value = api.to_float(value, -1)
    if value < 0:
        # zero and negative are not possible
        if default is _marker:
            raise ValueError("Zone size is not valid")
        return default

    def get_breakpoint_value(key):
        val = breakpoint.get(key)
        val = api.to_float(val, default=0)
        return None if val <= 0 else val

    if method == ZONE_SIZE_KEY:
        diameter_r = get_breakpoint_value("diameter_r")
        if diameter_r and value < diameter_r:
            # R: resistant
            return "R"

        diameter_s = get_breakpoint_value("diameter_s")
        if diameter_s and value >= diameter_s:
            # S: sensible
            return "S"

        if all([diameter_r, diameter_s]):
            # I: Susceptible at increased exposure
            return "I"

        # No zone size breakpoints set
        return ""

    elif method == MIC_KEY:

        mic_r = get_breakpoint_value("mic_r")
        if mic_r and value > mic_r:
            # R: resistant
            return "R"

        mic_s = get_breakpoint_value("mic_s")
        if mic_s and value <= mic_s:
            # S: sensible
            return "S"

        if all([mic_r, mic_s]):
            # I: Susceptible at increased exposure
            return "I"

        # No MIC breakpoints set
        return ""

    else:
        raise ValueError("Method not supported: {}".format(method))


def get_sensitivity_category_value(text, default=_marker):
    """Returns the choice value defined in the Sensitivity Category service for
    the option text passed-in

    :param text: text to look for its value counterpart in AST categories
    :type text: string
    :returns: the choices value for this AST category used in interims
    :rtype: string
    """
    # Resistance test (category) pre-defined choices
    choices = get_choices(SERVICES_SETTINGS[RESISTANCE_KEY])
    choices = dict(map(lambda choice: (choice[1], choice[0]), choices))
    value = choices.get(text, None)
    if value is None:
        if default is _marker:
            raise ValueError("Sensitivity category is not valid")
        return default
    return value


def is_ast_analysis(analysis):
    """Returns whether the analysis is an AST-type of analysis, with interims
    representing antibiotics and the analysis' ShortName a microorganism

    :param analysis: Analysis object
    :type analysis: IAnalysis
    :returns: True if is an analysis of AST type
    :rtype: bool
    """
    return analysis.getPointOfCapture() == AST_POINT_OF_CAPTURE


def get_choices(interim):
    """Returns a list of tuples made of (value, text) that represent the
    choices set for the given interim

    :param interim: interim field
    :type interim: dict
    :returns: A list of tuples (value, text)
    :rtype: list
    """
    choices = interim.get("choices", "")
    if not choices:
        return []
    choices = map(lambda choice: choice.split(":"), choices.split("|"))
    return map(lambda choice: (choice[0], choice[1]), choices)


def is_interim_empty(interim):
    """Returns whether an interim is empty or its value is considered empty

    :param interim: interim field
    :type interim: dict
    :returns: True if the value or text representation of this interim is empty
    :rtype: bool
    """
    text = get_interim_text(interim, default=None)
    return not text


def is_rejected_interim(interim):
    """Returns whether the interim represents a rejected antibiotic

    :param interim: interim field
    :type interim: dict
    :returns: True if the value or text representation of this interim is empty
    :rtype: bool
    """
    rejected = interim.get("status_rejected", None)
    if rejected:
        return True
    return False


def is_extrapolated_interim(interim):
    """Returns whether the interim represents an extrapolated antibiotic

    :param interim: interim field
    :type interim:dict
    :returns: True if the interim represents an extrapolated antibiotic
    :rtype: bool
    """
    primary = interim.get("primary", None)
    if primary:
        return True
    return False


def get_interim_text(interim, default=_marker):
    """Returns the text displayed for this interim field. Typically, the raw
    value when interim has no choices set and the choice text otherwise

    :param interim: interim field
    :type interim: dict
    :returns: The text representation of the value of this interim
    :rtype: string
    """
    value = interim.get("value", None)
    if value is None:
        if default is _marker:
            raise ValueError("Interim without value")
        return default

    choices = interim.get("choices", None)
    if not choices:
        # Value is the text
        return value

    val = api.parse_json(value)
    if isinstance(val, (list, tuple, set)):
        value = val

    if not isinstance(value, (list, tuple, set)):
        value = [value]

    choices = dict(get_choices(interim))
    texts = filter(None, [choices.get(v, None) for v in value])
    return "<br/>".join(texts)


def is_interim_editable(interim):
    """Returns whether the interim is editable or not

    :param interim: interim field
    :type interim: dict
    :returns: True if user can edit this interim
    :rtype: bool
    """
    if is_interim_empty(interim):
        return True

    statuses = ["to_be_verified", "verified", "rejected"]
    for status in statuses:
        status_id = "status_{}".format(status)
        if interim.get(status_id, False):
            return False

    return True


def get_extrapolated_antibiotics(antibiotics, uids=False):
    """Returns the list of antibiotics extrapolated from the antibiotics
    passed-in, without duplicates. Only extrapolated antibiotics that are not
    present in the list of representatives passed-in are returned

    :param antibiotics: representative antibiotics that have extrapolated
        antibiotics assigned
    :type: list of IAntibiotic
    :param uids: if true, returns UIDs. Returns Antibiotic objects otherwise
    :returns: the extrapolated list of antibiotics, without duplicates
    :rtype: list of UIDs or Antibiotic objects
    """
    if not isinstance(antibiotics, (list, tuple)):
        antibiotics = [antibiotics]

    # Extract extrapolated antibiotics from representative antibiotics
    extrapolated = map(lambda an: an.extrapolated_antibiotics, antibiotics)
    extrapolated = filter(None, extrapolated)

    # Flatten the list
    extrapolated = list(itertools.chain.from_iterable(extrapolated))
    extrapolated = filter(api.is_uid, extrapolated)

    # Remove existing antibiotics
    existing_uids = map(api.get_uid, antibiotics)
    extrapolated = filter(lambda uid: uid not in existing_uids, extrapolated)

    # Remove duplicates while keeping the order
    extrapolated = list(collections.OrderedDict.fromkeys(extrapolated))
    if uids:
        return extrapolated

    return map(api.get_object, extrapolated)


def get_extrapolated_interims(antibiotics, keyword):
    """Returns a list of interim fields that represent the antibiotics
    extrapolated from the antibiotics passed-in, without duplicates.
    Only extrapolated antibiotics that are not present in the list of
    representatives are returned

    :param antibiotics: representative antibiotics that have extrapolated
        antibiotics assigned
    :type: list of IAntibiotic
    :param keyword: keyword of the analysis service to extract the properties
        of a default interim field
    :type: str
    :returns: the extrapolated antibiotics as interim fields
    :rtype: list of dicts
    """
    interim_fields = []
    existing_uids = map(api.get_uid, antibiotics)
    for antibiotic in antibiotics:
        extrapolated = antibiotic.extrapolated_antibiotics or []
        for uid in extrapolated:
            if uid in existing_uids:
                continue

            # Do not display extrapolated antibiotics in results entry panel
            interim_field = to_interim(keyword, uid, hidden=True)
            interim_field.update({"primary": api.get_uid(antibiotic)})
            interim_fields.append(interim_field)
            existing_uids.append(uid)

    return interim_fields
