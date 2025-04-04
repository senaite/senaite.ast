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

from senaite.app.listing.interfaces import IListingView
from senaite.app.listing.interfaces import IListingViewAdapter
from senaite.ast.adapters.listing.services import NonASTServicesViewAdapter
from senaite.ast.interfaces import IASTAnalysis
from zope.component import adapter
from zope.interface import implementer


@adapter(IListingView)
@implementer(IListingViewAdapter)
class ManageAnalysesViewAdapter(NonASTServicesViewAdapter):
    """Adapter for Manage Analyses (as services) from Sample view
    """

    def before_render(self):
        # Do not display AST services
        super(ManageAnalysesViewAdapter, self).before_render()

        # Skip Sample's AST analyses
        is_ast = IASTAnalysis.providedBy
        analyses = self.listing.analyses.items()
        analyses = filter(lambda an: not is_ast(an[1]), analyses)
        self.listing.analyses = dict(analyses)
