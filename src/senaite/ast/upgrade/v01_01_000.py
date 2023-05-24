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

from bika.lims import api
from senaite.ast import logger
from senaite.ast import PRODUCT_NAME
from senaite.ast.calc import update_sensitivity_result
from senaite.ast.config import RESISTANCE_KEY
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
    import pdb;pdb.set_trace()
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

        if obj.getResult() not in ["-", "NA"]:
            obj._p_deactivate()
            continue

        # Update the result
        logger.info("Updatiing {}".format(repr(obj)))
        update_sensitivity_result(obj)

        # Flush the object from memory
        obj._p_deactivate()

    logger.info("Fix wrong AST results [DONE]")
