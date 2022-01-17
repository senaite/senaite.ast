# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.AST.
#
# SENAITE.AST is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
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
# Copyright 2020-2021 by it's authors.
# Some rights reserved, see README and LICENSE.

from bika.lims import api
from bika.lims.catalog import CATALOG_ANALYSIS_LISTING
from senaite.ast import logger
from senaite.ast import PRODUCT_NAME
from senaite.ast import PROFILE_ID
from senaite.ast.setuphandlers import add_setup_folders
from senaite.ast.setuphandlers import setup_ast_calculation
from senaite.ast.setuphandlers import setup_ast_category
from senaite.ast.setuphandlers import setup_ast_services
from senaite.ast.setuphandlers import setup_navigation_types
from senaite.core.upgrade import upgradestep
from senaite.core.upgrade.utils import UpgradeUtils
from senaite.core.catalog import SETUP_CATALOG

version = "1.0.0"


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

    # Additional BreakpointsTable(s) type
    setup.runImportStepFromProfile(PROFILE_ID, "typeinfo")
    setup.runImportStepFromProfile(PROFILE_ID, "factorytool")
    setup.runImportStepFromProfile(PROFILE_ID, "workflow")

    # Setup folders
    add_setup_folders(portal)

    # Configure visible navigation items
    setup_navigation_types(portal)

    # Setup calculations and services
    setup_ast_calculation(portal)
    setup_ast_category(portal)
    setup_ast_services(portal)

    # Add 'uid' in interims dict of ast-like analyses
    fix_uid_ast_interims(portal)

    # Remove AST-like services from profiles and templates
    remove_ast_from_profiles(portal)
    remove_ast_from_templates(portal)

    logger.info("{0} upgraded to version {1}".format(PRODUCT_NAME, version))
    return True


def fix_uid_ast_interims(portal):
    """Walks through al ast-like analyses and add the uid of the antibiotic they
    relate to
    """
    logger.info("Fixing antibiotic UIDs in interims ...")
    query = {
        "getPointOfCapture": "ast",
        "sort_on": "sortable_title",
        "sort_order": "ascending",
    }
    analyses = api.search(query, CATALOG_ANALYSIS_LISTING)
    total = len(analyses)
    for num, analysis in enumerate(analyses):
        if num % 100 == 0:
            logger.info("Fixing antibiotic UIDs in interims: {0}/{1}"
                        .format(num, total))
        analysis = api.get_object(analysis)
        interims = analysis.getInterimFields()
        for interim in interims:
            uid = interim.get("uid")
            if uid:
                continue

            keyword = interim.get("keyword")
            antibiotic = get_antibiotic(keyword)
            if antibiotic:
                abx_uid = api.get_uid(antibiotic)
                interim.update({"uid": abx_uid})

        analysis.setInterimFields(interims)

    logger.info("Fixing antibiotic UIDs in interims [DONE]")


def get_antibiotic(abbreviation):
    objects = api.get_setup().antibiotics.objectValues()
    objects = filter(lambda a: a.abbreviation == abbreviation, objects)
    objects = filter(None, objects)
    if objects:
        return objects[0]
    return None


def get_ast_services_uids(portal):
    """Returns the list of AST-like services
    """
    query = {"portal_type": "AnalysisService",
             "point_of_capture": "ast"}
    brains = api.search(query, SETUP_CATALOG)
    return map(api.get_uid, brains)


def remove_ast_from_profiles(portal):
    """Removes AST analyses assigned to Analysis Profiles
    """
    logger.info("Removing AST-like analyses from profiles ...")
    ast_uids = get_ast_services_uids(portal)
    query = {
        "portal_type": "AnalysisProfile"
    }
    brains = api.search(query, SETUP_CATALOG)
    for brain in brains:
        obj = api.get_object(brain)
        services = obj.getRawService() or []
        services = filter(lambda s: s not in ast_uids, services)
        obj.setService(services)
    logger.info("Removing AST-like analyses from profiles [DONE]")


def remove_ast_from_templates(portal):
    """Remove AST analyses assigned to AR Templates
    """
    logger.info("Removing AST-like analyses from templates ...")
    ast_uids = get_ast_services_uids(portal)
    query = {
        "portal_type": "ARTemplate"
    }
    brains = api.search(query, SETUP_CATALOG)
    for brain in brains:
        obj = api.get_object(brain)
        ans = obj.getAnalyses()
        ans = filter(lambda an: an.get("service_uid") not in ast_uids, ans)
        obj.setAnalyses(ans)

        settings = obj.getAnalysisServicesSettings()
        settings = filter(lambda an: an.get("uid") not in ast_uids, settings)
        obj.setAnalysisServicesSettings(settings)

    logger.info("Removing AST-like analyses from templates [DONE]")
