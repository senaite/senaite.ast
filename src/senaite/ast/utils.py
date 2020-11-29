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
from bika.lims import workflow as wf
from bika.lims.catalog import SETUP_CATALOG
from bika.lims.interfaces import IInternalUse
from bika.lims.interfaces import ISubmitted
from bika.lims.interfaces import IVerified
from bika.lims.utils.analysis import create_analysis
from bika.lims.workflow import doActionFor
from senaite.ast import logger
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
    """Returns a new analysis id for an hypothetic new test with given keyword
    to prevent clashes with ids of other analyses from same sample
    """
    new_id = analysis_keyword
    analyses = sample.getAnalyses(getKeyword=analysis_keyword)
    if analyses:
        new_id = "{}-{}".format(analysis_keyword, len(analyses))
    return new_id


def create_ast_analysis(sample, keyword, microorganism, antibiotics):
    """Creates a new AST analysis
    """
    # Convert antibiotics to interims
    interims = map(lambda ab: to_interim(keyword, ab), antibiotics)

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

    # Assign the antibiotics as interims
    analysis.setInterimFields(interims)

    # Compute all combinations of interim/antibiotic and possible result and
    # and generate the result options for this analysis (the "Result" field is
    # never displayed and is only used for reporting)
    result_options = get_result_options(analysis)
    analysis.setResultOptions(result_options)

    # Apply the IASTAnalysis and IInternalUser marker interfaces
    alsoProvides(analysis, IASTAnalysis)
    alsoProvides(analysis, IInternalUse)

    # Initialize the analysis and reindex
    doActionFor(analysis, "initialize")
    analysis.reindexObject()

    return analysis


def update_ast_analysis(analysis, antibiotics):
    # There is nothing to do if the analysis has been verified
    analysis = api.get_object(analysis)
    if IVerified.providedBy(analysis):
        return

    # Convert antibiotics to interims
    keyword = analysis.getKeyword()
    interims = map(lambda ab: to_interim(keyword, ab), antibiotics)

    # Compare the interims passed-in with those assigned to the analysis
    keys = map(lambda i: i.get("keyword"), analysis.getInterimFields())
    abx = filter(lambda a: a["keyword"] not in keys, interims)
    if not abx:
        # Analysis has all antibiotics assigned already
        return

    if ISubmitted.providedBy(analysis):
        # Analysis has been submitted already, retract
        succeed, message = wf.doActionFor(analysis, "retract")
        if not succeed:
            path = api.get_path(analysis)
            logger.error("Cannot retract analysis '{}'".format(path))
            return

    # Assign the antibiotics
    analysis.setInterimFields(interims)

    # Compute all combinations of interim/antibiotic and possible result and
    # and generate the result options for this analysis (the "Result" field is
    # never displayed and is only used for reporting)
    result_options = get_result_options(analysis)
    analysis.setResultOptions(result_options)

    # Apply the IASTAnalysis marker interface (just in case)
    alsoProvides(analysis, IASTAnalysis)

    analysis.reindexObject()


def to_interim(keyword, antibiotic):
    """Converts a list of antibiotics to a list of interims
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
            result_value = str(len(options))
            option = to_result_option(interim, choice, result_value)
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
