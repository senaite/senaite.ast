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
# Copyright 2020-2021 by it's authors.
# Some rights reserved, see README and LICENSE.

from senaite.ast.config import BREAKPOINTS_TABLE_KEY
from senaite.ast.config import RESISTANCE_KEY
from senaite.ast.config import ZONE_SIZE_KEY
from senaite.ast.interfaces import IASTAnalysis
from senaite.ast.utils import get_ast_siblings
from senaite.core.datamanagers.analysis import RoutineAnalysisDataManager
from zope.component import adapter


@adapter(IASTAnalysis)
class ASTAnalysisDataManager(RoutineAnalysisDataManager):
    """Data Manager for AST-like analyses
    """

    def recalculate_results(self, obj, recalculated=None):
        recalculated = super(ASTAnalysisDataManager, self).\
            recalculate_results(obj, recalculated=recalculated)

        if obj.getKeyword() not in [ZONE_SIZE_KEY, BREAKPOINTS_TABLE_KEY]:
            return recalculated

        # Add the sensitivity category analysis too, so the results for this
        # test are automatically refreshed in results entry listing when the
        # user saves results for either zone size or breakpoints
        siblings = get_ast_siblings(obj)
        res = filter(lambda s: s.getKeyword() == RESISTANCE_KEY, siblings)
        recalculated.update(res)
        return recalculated
