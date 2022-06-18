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
# Copyright 2020-2022 by it's authors.
# Some rights reserved, see README and LICENSE.

import copy
from datetime import datetime

from bika.lims import api
from senaite.ast import messageFactory as _
from senaite.ast.config import IDENTIFICATION_KEY
from senaite.ast.interfaces import IASTAnalysis
from senaite.core.api import dtime as dt
from senaite.core.catalog import SETUP_CATALOG


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

    # Update interim fields with status information. This makes a "simulated"
    # partial entry of results possible: if user adds new antibiotics, the
    # analysis will rollback to its previous status and new antibiotics will
    # be added as new interim fields, but existing ones, with an status
    # attribute, will be rendered in read-only mode
    update_interim_status(analysis)


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
