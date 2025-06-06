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

import zope.i18n.format
from z3c.form.converter import FormatterValidationError

DECIMAL_PATTERN = u'#,##0.######;-#,##0.######'


def toFieldValue(self, value):
    """See interfaces.IDataConverter"""
    if value == u'':
        return self.field.missing_value
    try:
        return self.formatter.parse(value, pattern=DECIMAL_PATTERN)
    except zope.i18n.format.NumberParseError:
        raise FormatterValidationError(self.errorMessage, value)
