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

from senaite.ast import logger
from senaite.ast.config import BREAKPOINTS_TABLE_KEY
from senaite.ast.config import DISK_CONTENT_KEY
from senaite.ast.config import RESISTANCE_KEY
from senaite.ast.config import ZONE_SIZE_KEY
from senaite.ast.interfaces import IASTAnalysis
from senaite.ast.utils import get_ast_siblings
from senaite.ast.utils import is_ast_analysis
from senaite.ast.utils import is_interim_editable
from senaite.core.datamanagers import RoutineAnalysisDataManager
from zope.component import adapter


@adapter(IASTAnalysis)
class ASTAnalysisDataManager(RoutineAnalysisDataManager):
    """Data Manager for AST-like analyses
    """

    def get_antibiotic_interim(self, keyword, default=None):
        """Returns the interim that represents the antibiotic with the given
        keyword, but only if the context is an AST-like analysis
        """
        if not is_ast_analysis(self.context):
            return default

        for interim in self.context.getInterimFields():
            if interim.get("keyword") == keyword:
                return interim

        return default

    def set(self, name, value):
        """Set analysis field/interim value
        """
        # Check if an antibiotic/interim of an AST analysis
        antibiotic = self.get_antibiotic_interim(name)
        if antibiotic and not is_interim_editable(antibiotic):
            logger.error("Interim field '{}' not writeable!".format(name))
            return []

        # rely on the base class
        base = super(ASTAnalysisDataManager, self)
        return base.set(name, value)

    def recalculate_results(self, obj, recalculated=None):
        recalculated = super(ASTAnalysisDataManager, self).\
            recalculate_results(obj, recalculated=recalculated)

        if obj.getKeyword() not in [ZONE_SIZE_KEY, BREAKPOINTS_TABLE_KEY]:
            return recalculated

        # Add the sensitivity category and disk dosage analysis too, so the
        # results for this test are automatically refreshed in results entry
        # listing when the user saves results for either zone size or
        # breakpoints
        keep = [RESISTANCE_KEY, DISK_CONTENT_KEY]
        siblings = get_ast_siblings(obj)
        res = filter(lambda s: s.getKeyword() in keep, siblings)
        recalculated.update(res)
        return recalculated
