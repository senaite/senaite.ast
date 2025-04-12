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

from bika.lims import api
from senaite.ast import logger
from senaite.ast import PRODUCT_NAME
from senaite.ast.calc import update_sensitivity_result
from senaite.ast.config import DISK_CONTENT_KEY
from senaite.ast.config import MIC_KEY
from senaite.ast.config import RESISTANCE_KEY
from senaite.ast.config import SERVICES_SETTINGS
from senaite.ast.config import ZONE_SIZE_KEY
from senaite.ast.setuphandlers import setup_ast_services
from senaite.core.catalog import ANALYSIS_CATALOG
from senaite.core.upgrade import upgradestep
from senaite.core.upgrade.utils import uncatalog_brain
from senaite.core.upgrade.utils import UpgradeUtils

version = "1.1.0"


@upgradestep(PRODUCT_NAME, version)
def upgrade(tool):
    portal = tool.aq_inner.aq_parent
    setup = portal.portal_setup
    ut = UpgradeUtils(portal)
    ver_from = ut.getInstalledVersion(PRODUCT_NAME)

    if ut.isOlderVersion(PRODUCT_NAME, version):
        logger.info("Skipping upgrade of {0}: {1} > {2}".format(
            PRODUCT_NAME, ver_from, version))
        return True

    logger.info("Upgrading {0}: {1} -> {2}".format(PRODUCT_NAME, ver_from,
                                                   version))

    # -------- ADD YOUR STUFF BELOW --------

    logger.info("{0} upgraded to version {1}".format(PRODUCT_NAME, version))
    return True


def fix_wrong_results_resistance(tool):
    """Walks thorugh "to_be_verified" AST resistance tests and forces the
    update of the result if it's current result is '-' or 'NA'
    """
    logger.info("Fix wrong AST results ...")
    query = {
        "portal_type": "Analysis",
        "review_state": "to_be_verified",
        "getKeyword": RESISTANCE_KEY,
    }
    brains = api.search(query, ANALYSIS_CATALOG)

    total = len(brains)
    for num, brain in enumerate(brains):
        if num and num % 100 == 0:
            logger.info("Processed objects: {}/{}".format(num, total))

        try:
            obj = api.get_object(brain, default=None)
        except AttributeError:
            obj = None

        if not obj:
            uncatalog_brain(brain)
            continue

        if obj.getResult() not in ["-", "NA"]:
            obj._p_deactivate()
            continue

        # Update the result
        logger.info("Updating {}".format(repr(obj)))
        update_sensitivity_result(obj)

        # Flush the object from memory
        obj._p_deactivate()

    logger.info("Fix wrong AST results [DONE]")


def setup_mic_support(tool):
    """Adds the MIC value service to support Minimum Inhibitory Concentration
    method to determine microbial susceptibility to antibiotics
    """
    logger.info("Setup MIC support ...")
    portal = tool.aq_inner.aq_parent
    setup_ast_services(portal, update_existing=False)
    logger.info("Setup MIC support [DONE]")


def setup_mic_fraction_field(tool):
    """Walks through 'MIC value (μg/mL)' analyses and resets their type from
    'string' to 'fraction' and sets their size to '5'
    """
    logger.info("Setup fraction type for MIC value fields ...")
    query = {
        "portal_type": "Analysis",
        "getKeyword": [MIC_KEY],
    }
    brains = api.search(query, ANALYSIS_CATALOG)
    total = len(brains)
    for num, brain in enumerate(brains):
        if num and num % 100 == 0:
            logger.info("Processed objects: {}/{}".format(num, total))

        try:
            obj = api.get_object(brain, default=None)
        except AttributeError:
            obj = None

        if not obj:
            uncatalog_brain(brain)
            continue

        # Restore the size of all interim fields to 3
        interim_fields = obj.getInterimFields()
        for interim_field in interim_fields:
            interim_field["size"] = "5"
            interim_field["result_type"] = "fraction"
        obj.setInterimFields(interim_fields)
        obj._p_deactivate()

    logger.info("Setup fraction type for MIC value fields [DONE]")


def resize_ast_numeric_fields(tool):
    """Walks through AST analyses of 'Disk content (μg)', 'Zone diameter (mm)'
    and 'MIC value (μg/mL)' and resets the size of their input element from '1'
    to '3', cause they got shrinked with
    https://github.com/senaite/senaite.app.listing/pull/125
    """
    logger.info("Resizing AST numeric fields ...")
    query = {
        "portal_type": "Analysis",
        "getKeyword": [DISK_CONTENT_KEY, ZONE_SIZE_KEY, MIC_KEY],
    }
    brains = api.search(query, ANALYSIS_CATALOG)
    total = len(brains)
    for num, brain in enumerate(brains):
        if num and num % 100 == 0:
            logger.info("Processed objects: {}/{}".format(num, total))

        try:
            obj = api.get_object(brain, default=None)
        except AttributeError:
            obj = None

        if not obj:
            uncatalog_brain(brain)
            continue

        # get the size of the analysis as defined in config
        size = SERVICES_SETTINGS[obj.getKeyword()]["size"]

        # Restore the size of all interim fields to 3
        interim_fields = obj.getInterimFields()
        for interim_field in interim_fields:
            interim_field["size"] = size
        obj.setInterimFields(interim_fields)
        obj._p_deactivate()

    logger.info("Resizing AST numeric fields ...")
