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
from senaite.ast.config import AST_POINT_OF_CAPTURE
from senaite.ast.config import REPORT_EXTRAPOLATED_KEY
from senaite.core.catalog import ANALYSIS_CATALOG
from senaite.core.upgrade import upgradestep
from senaite.core.upgrade.utils import UpgradeUtils

version = "1.3.0"
profile = "profile-{0}:default".format(PRODUCT_NAME)


@upgradestep(PRODUCT_NAME, version)
def upgrade(tool):
    portal = tool.aq_inner.aq_parent
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


def set_ast_analyses_scientific_name(tool):
    """Mark existing AST analyses as scientific names
    """
    logger.info("Set ScientificName for AST analyses ...")
    query = {
        "portal_type": "Analysis",
        "getPointOfCapture": AST_POINT_OF_CAPTURE,
    }
    brains = api.search(query, ANALYSIS_CATALOG)
    total = len(brains)
    for num, brain in enumerate(brains):

        if num and num % 1000 == 0:
            logger.info("Set ScientificName for AST analyses %s/%s"
                        % (num, total))

        analysis = api.get_object(brain)
        if analysis.getScientificName():
            continue

        # ScientificName is not indexed, no need to reindex the analysis
        analysis.setScientificName(True)
        analysis._p_deactivate()

    logger.info("Set ScientificName for AST analyses [DONE]")


def allow_empty_selective_reporting(tool):
    """Allows empty values for the result variables of the analyses that store
    the selective reporting of extrapolated antibiotics, so they can be
    submitted when no extrapolated antibiotic is selected
    """
    logger.info("Allow empty selective reporting of extrapolated abx ...")
    query = {
        "portal_type": "Analysis",
        "getKeyword": REPORT_EXTRAPOLATED_KEY,
        "review_state": ["registered", "unassigned", "assigned"],
    }
    brains = api.search(query, ANALYSIS_CATALOG)
    total = len(brains)
    for num, brain in enumerate(brains):

        if num and num % 1000 == 0:
            logger.info("Allow empty selective reporting of extrapolated abx "
                        "%s/%s" % (num, total))

        analysis = api.get_object(brain)
        interims = analysis.getInterimFields()
        if not interims:
            continue

        for interim in interims:
            interim["allow_empty"] = True

        # Interim fields are not indexed, no need to reindex the analysis
        analysis.setInterimFields(interims)
        analysis._p_deactivate()

    logger.info("Allow empty selective reporting of extrapolated abx [DONE]")
