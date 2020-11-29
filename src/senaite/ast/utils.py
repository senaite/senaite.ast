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
from bika.lims.interfaces import ISubmitted
from bika.lims.interfaces import IVerified
from bika.lims.utils.analysis import create_analysis
from bika.lims.workflow import doActionFor
from senaite.ast import logger
from senaite.ast.config import SERVICES_SETTINGS


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
    # Get the analysis title
    title = get_analysis_title(keyword, microorganism)

    # Convert antibiotics to interims
    interims = map(lambda ab: to_interim(keyword, ab), antibiotics)

    # Create a new ID to prevent clashes
    new_id = new_analysis_id(sample, keyword)

    # Create the analysis
    service = get_service(keyword)
    analysis = create_analysis(sample, service, id=new_id)

    # Assign the name of the microorganism as the title
    analysis.setTitle(title)

    # Assign the antibiotics as interims
    analysis.setInterimFields(interims)

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
        "type": properties.get("type", "")
    }


def get_analysis_title(keyword, microorganism):
    """Returns the analysis title for the service keyword and microorganism
    """
    title = SERVICES_SETTINGS[keyword]["title"]
    obj = api.get_object(microorganism)
    return title.format(api.get_title(obj))
