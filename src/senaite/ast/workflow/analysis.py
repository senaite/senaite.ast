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
from datetime import datetime

from bika.lims import api
from bika.lims.interfaces import IAuditable
from bika.lims.interfaces import IInternalUse
from bika.lims.interfaces import ISubmitted
from senaite.ast import messageFactory as _
from senaite.ast import utils
from senaite.ast.config import IDENTIFICATION_KEY
from senaite.ast.config import REPORT_KEY
from senaite.ast.config import RESISTANCE_KEY
from senaite.ast.interfaces import IASTAnalysis
from senaite.core.api import dtime as dt
from senaite.core.catalog import SETUP_CATALOG
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
    empties = map(utils.is_interim_empty, analysis.getInterimFields())
    if any(empties):
        return

    # Update interim fields with status information. This makes a "simulated"
    # partial entry of results possible: if user adds new antibiotics, the
    # analysis will rollback to its previous status and new antibiotics will
    # be added as new interim fields, but existing ones, with an status
    # attribute, will be rendered in read-only mode
    update_interim_status(analysis)

    # All siblings for same microorganism and sample have to be submitted
    siblings = utils.get_ast_siblings(analysis)
    submitted = map(ISubmitted.providedBy, siblings)
    if not all(submitted):
        return

    # Calculate the hidden analyses and results
    analyses = siblings + [analysis]
    keywords = map(lambda an: an.getKeyword(), analyses)
    analyses = dict(zip(keywords, analyses))

    # We only do report results from "sensitivity category" analysis
    sensitivity = analyses.get(RESISTANCE_KEY)

    # Results are the values (R/I/S) set for resistance' interim fields
    results = sensitivity.getInterimFields()

    # Find out the resistance results to report
    report = analyses.get(REPORT_KEY)
    if report:
        # The results to be reported are defined by the Y/N values set for the
        # interim fields of the "selective reporting" analysis
        to_report = report.getInterimFields()

        # XXX senaite.app.listing has no support boolean type for interim fields
        to_report = filter(lambda k: k.get("value") == "1", to_report)

        # Get the abbreviation of microorganisms (keyword)
        keywords = map(lambda k: k.get("keyword"), to_report)

        # Filter the interim fields from resistance
        results = filter(lambda r: r.get("keyword") in keywords, results)

    # The "selected" result options are those to be reported
    options = sensitivity.getResultOptions()

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
    noLongerProvides(sensitivity, IAuditable)

    # Set the final result
    capture_date = sensitivity.getResultCaptureDate()
    sensitivity.setResult(result)
    sensitivity.setResultCaptureDate(capture_date)

    # We do want to report this sensitivity category analysis
    if IInternalUse.providedBy(sensitivity):
        noLongerProvides(sensitivity, IInternalUse)

    # Re-enable the audit for this analysis
    alsoProvides(sensitivity, IAuditable)


def after_verify(analysis):
    """Event fired when an analysis is verified
    """
    if not IASTAnalysis.providedBy(analysis):
        return

    # Update interim fields with status information. This makes a "simulated"
    # partial entry of results possible: if user adds new antibiotics, the
    # analysis will rollback to its previous status and new antibiotics will
    # be added as new interim fields, but existing ones, with an status
    # attribute, will be rendered in read-only mode
    update_interim_status(analysis)


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


def copy_interims(source, destination, keep_status=False):
    """Copies the interims from the source analysis to destination analysis
    """
    interim_fields = copy.deepcopy(source.getInterimFields())
    for interim in interim_fields:
        # Reset value
        interim.update({"value": ""})

        if not keep_status:
            # Remove status attributes from interim fields
            skip = filter(lambda k: k.startswith("status_"), interim.keys())
            map(lambda key: interim.pop(key), skip)

    # Set interims fields to destination
    destination.setInterimFields(interim_fields)


def update_interim_status(analysis):
    """Updates interim fields with the analysis status information
    """
    status = api.get_review_status(analysis)
    status_id = "status_{}".format(status)
    status_by = "status_{}_by".format(status)
    status_date = dt.to_iso_format(datetime.now())
    user_id = api.get_current_user().id
    interim_fields = copy.deepcopy(analysis.getInterimFields())
    for interim_field in interim_fields:
        interim_field.update({
            status_id: status_date,
            status_by: user_id})
    analysis.setInterimFields(interim_fields)
