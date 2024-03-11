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
# Copyright 2020-2024 by it's authors.
# Some rights reserved, see README and LICENSE.

from bika.lims import api
from senaite.ast import logger
from senaite.ast import PRODUCT_NAME
from senaite.ast.config import AST_POINT_OF_CAPTURE
from senaite.ast.setuphandlers import setup_workflows
from senaite.core.catalog import ANALYSIS_CATALOG
from senaite.core.upgrade import upgradestep
from senaite.core.upgrade.utils import UpgradeUtils

version = "1.1.0"
profile = "profile-{0}:default".format(PRODUCT_NAME)


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


def setup_reject_antibiotics(tool):
    logger.info("Setup reject antibiotics transition ...")
    portal = tool.aq_inner.aq_parent

    # import rolemap and workflow
    setup = portal.portal_setup
    setup.runImportStepFromProfile(profile, "rolemap")
    setup.runImportStepFromProfile(profile, "workflow")

    # setup custom workflow modifs
    setup_workflows(portal)

    # update role mappings
    statuses = ["assigned", "unassigned", "to_be_verified", "verified"]
    cat = api.get_tool(ANALYSIS_CATALOG)
    brains = cat(portal_type="Analysis", review_state=statuses,
                 getPointOfCapture=AST_POINT_OF_CAPTURE)
    map(update_role_mappings_for, brains)

    logger.info("Setup reject antibiotics transition [DONE]")


def update_role_mappings_for(object_or_brain):
    """Update role mappings for the specified object
    """
    obj = api.get_object(object_or_brain)
    path = api.get_path(obj)
    logger.info("Updating workflow role mappings for {} ...".format(path))
    tool = api.get_tool("portal_workflow")
    for wf_id in api.get_workflows_for(obj):
        wf = tool.getWorkflowById(wf_id)
        wf.updateRoleMappingsFor(obj)
        obj.reindexObject(idxs=["allowedRolesAndUsers"])
