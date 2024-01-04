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

from senaite.ast import messageFactory as _

# Value for PointOfCapture field for AST-like analyses. This is used to identify
# AST-like analyses and also to not display them in the classic results entry
# view, but in an AST-specific section for results introduction in Sample view
AST_POINT_OF_CAPTURE = "ast"

# Analysis Category name AST Services will be added into
SERVICE_CATEGORY = _("Antibiotic Sensitivity Testing (AST)")

# Keyword of the Analysis Service to be used as the template for the creation
# of zone size (mm) results. This service is automatically created on install
# and is not editable
ZONE_SIZE_KEY = "senaite_ast_zone"

# Keyword of the Analysis Service to be used as the template for the creation
# of minium inhibitory concentration (MIC) results. This service is
# automatically created on install and is not editable
MIC_KEY = "senaite_ast_mic"

# Keyword of the Analysis Service to be used as the template for the creation
# disk content (potency) analyses. This is the concentration of antimicrobial
# agent added to the filter paper disk to determine in vitro antimicrobial
# susceptibility testing results following a standardised disk diffusion method
# equivalent to disk load, disk mass, disk strength, and disk charge. This
# Service is automatically created on install and is not editable
DISK_CONTENT_KEY = "senaite_ast_potency"

# Keyword of the Analysis Service to be used to store the clinical breakpoints
# table to use to calculate the susceptibility testing category
# ('senaite_ast_resistance') automatically based on the zone size (mm)
# submitted for a given tuple of Microorganism - Antibiotic
BREAKPOINTS_TABLE_KEY = "senaite_ast_breakpoint"

# Keyword of the Analysis Service to be used as the template for the creation
# of AST analyses. This Service is automatically created on install and is not
# editable
RESISTANCE_KEY = "senaite_ast_resistance"

# Keyword of the Analysis Service to be used as the template for the creation
# of analyses that will be used to tell whether the AST result has to be
# reported in results report or not
REPORT_KEY = "senaite_ast_report"

# Keyword of the Analysis Service for the identification of microorganisms
# This analysis service is used for the automatic selection of microorganisms
# to include in an AST testing when an AST Panel is selected. If this service
# is not present, the system assign all microorganisms from the panel
IDENTIFICATION_KEY = "senaite_ast_identification"

# Keyword of the Analysis Service used to choose the extrapolated antibiotics
# to be reported in results report
REPORT_EXTRAPOLATED_KEY = "senaite_ast_report_extrapolated"

# Title for the AST calculation object. This calculation allows AST machinery
# to assign a final result by its own, without prompting the user
AST_CALCULATION_TITLE = "senaite_ast_calc"

# Description for autogenerated contents
AUTOGENERATED = _(u"Autogenerated by senaite.ast")

# Id of the Diffusion Disk method
METHOD_DIFFUSION_DISK_ID = "diffusion_disk"

# Id of the Minimum Inhibitory Concentration (MIC) method
METHOD_MIC_ID = "mic"

# Available methods to determine microbial susceptibility to antibiotics
AST_METHODS = (
    (METHOD_DIFFUSION_DISK_ID, _(
        u"vocab_astmethod_diffusiondisk",
        default=u"Diffusion disk")
     ),
    (METHOD_MIC_ID, _(
        u"vocab_astmethod_mic",
        default=u"Minimum Inhibitory Concentration (MIC)")
     )
)

# Settings for analyses creation
SERVICES_SETTINGS = {

    RESISTANCE_KEY: {
        "title": "{} - " + _(u"Category"),
        "description":
            _(u"The susceptibility testing category defines the likelihood of "
              u"therapeutic success when a given microorganism is exposed to "
              u"a specific antimicrobial agent. Three different categories "
              u"are available in accordance with EUCAST (European Committee "
              u"on Antimicrobial Susceptibility Testing): S (Susceptible), I "
              u"(Susceptible, increased exposure) and R (Resistant)"),
        "choices": "0:|1:S|2:I|3:R",
        "sort_key": 530,
        "string_result": True,
        "point_of_capture": AST_POINT_OF_CAPTURE,
        "calculation": AST_CALCULATION_TITLE,
    },

    BREAKPOINTS_TABLE_KEY: {
        "title": "{} - " + _(u"Breakpoints table"),
        "description":
            _(u"Default clinical breakpoints table to use for the automatic"
              u"calculation of the susceptibility testing category when a "
              u"zone diameter for a given microorganism - antibiotic tuple is "
              u"submitted."),
        # XXX This is a choices field, but choices are populated on creation
        "choices": "",
        "sort_key": 505,
        "string_result": True,
        "point_of_capture": AST_POINT_OF_CAPTURE,
        "calculation": AST_CALCULATION_TITLE,
    },

    DISK_CONTENT_KEY: {
        "title": "{} - " + _(u"Disk content (μg)"),
        "description":
            _(u"Concentration of antimicrobial agent added to the filter "
              u"paper disk to determine in vitro antimicrobial susceptibility "
              u"testing results following a standardised disk diffusion "
              u"method equivalent to disk load, disk mass, disk strength, and "
              u"disk charge."),
        "size": "3",
        "sort_key": 510,
        "string_result": True,
        "point_of_capture": AST_POINT_OF_CAPTURE,
        "calculation": AST_CALCULATION_TITLE,
    },

    ZONE_SIZE_KEY: {
        "title": "{} - " + _(u"Zone diameter (mm)"),
        "description":
            _(u"The diameter of inhibition zone (DIZ) is a circular area "
              u"around the spot of the antibiotic in which the bacteria "
              u"colonies do not grow. The larger the diameter, the more "
              u"potent is the antimicrobial. It is used to determine whether "
              u"a bacteria is resistant, intermediately sensitive or "
              u"susceptible to an antibiotic."),
        "size": "3",
        "sort_key": 520,
        "string_result": True,
        "point_of_capture": AST_POINT_OF_CAPTURE,
        "calculation": AST_CALCULATION_TITLE,
    },

    MIC_KEY: {
        "title": "{} - " + _(u"MIC value (μg/mL)"),
        "description":
            _(u"The Minimum Inhibitory Concentration (MIC) value is the "
              u"lowest concentration of an antibiotic at which bacterial "
              u"growth is completely inhibited. The lower the MIC, the more "
              u"potent the antimicrobial. It is used to determine whether a "
              u"bacteria is resistant, intermediately sensitive or "
              u"susceptible to an antibiotic."),
        "size": "5",
        "sort_key": 520,
        "string_result": True,
        "point_of_capture": AST_POINT_OF_CAPTURE,
        "calculation": AST_CALCULATION_TITLE,
    },

    REPORT_KEY: {
        "title": "{} - " + _(u"Report"),
        "choices": "0:|1:Y|2:N",
        # XXX senaite.app.listing has no support for boolean types (interim)
        "type": "boolean",
        "sort_key": 540,
        "string_result": True,
        "point_of_capture": AST_POINT_OF_CAPTURE,
        "calculation": AST_CALCULATION_TITLE,
    },

    REPORT_EXTRAPOLATED_KEY: {
        "title": "{} - " + _(u"Report extrapolated"),
        "description":
            _(u"Selection of the antibiotics to be included in results report "
              u"that their sensitivity is extrapolated from antibiotic "
              u"representatives"),
        # XXX This is a choices field, but choices are populated on creation
        "choices": "",
        "type": "multichoice",
        "sort_key": 550,
        "string_result": True,
        "point_of_capture": AST_POINT_OF_CAPTURE,
        "calculation": AST_CALCULATION_TITLE,
    },

    IDENTIFICATION_KEY: {
        "title": _(u"Microorganism identification"),
        "sort_key": 500,
        # The options are the list of microorganisms and are automatically
        # added when the corresponding analysis is initialized
        "options_type": "multiselect",
        "string_result": False,
        "point_of_capture": "lab",
        "calculation": None,
    }

}
