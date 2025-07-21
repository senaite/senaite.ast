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

import transaction
from bika.lims import api
from senaite.ast import logger
from senaite.ast import PRODUCT_NAME
from senaite.ast.setuphandlers import setup_catalogs
from senaite.core.catalog import SETUP_CATALOG
from senaite.core.upgrade import upgradestep
from senaite.core.upgrade.utils import UpgradeUtils
from senaite.core.api.catalog import get_catalog
from senaite.core.api.catalog import get_index

version = "1.3.0"
profile = "profile-{0}:default".format(PRODUCT_NAME)


@upgradestep(PRODUCT_NAME, version)
def upgrade(tool):
    portal = tool.aq_inner.aq_parent
    ut = UpgradeUtils(portal)
    ver_from = ut.getInstalledVersion(PRODUCT_NAME)

    # if ut.isOlderVersion(PRODUCT_NAME, version):
    #     logger.info("Skipping upgrade of {0}: {1} > {2}".format(
    #         PRODUCT_NAME, ver_from, version))
    #     return True

    logger.info("Upgrading {0}: {1} -> {2}".format(PRODUCT_NAME, ver_from,
                                                   version))

    # -------- ADD YOUR STUFF BELOW --------

    logger.info("{0} upgraded to version {1}".format(PRODUCT_NAME, version))
    return True


def add_guideline_index(tool):
    """Add guideline field index to SETUP_CATALOG for BreakpointsTable listing"""
    logger.info("Adding guideline field index...")

    portal = tool.aq_inner.aq_parent
    setup_catalogs(portal)
    
    cat = get_catalog(SETUP_CATALOG)
    # Reindex existing BreakpointsTable objects to populate the guideline metadata
    logger.info("Reindexing existing BreakpointsTable objects...")
    brains = api.search({"portal_type": "BreakpointsTable"}, SETUP_CATALOG)

    for brain in brains:
        obj = api.get_object(brain)
        if not obj:
            continue
        # Reindex the object with metadata update to populate the new column
        cat.reindexObject(obj, update_metadata=True)
        obj._p_deactivate()

    transaction.commit()

    logger.info("Reindexed {} BreakpointsTable objects".format(len(brains)))
    logger.info("Adding guideline field index [DONE]")
