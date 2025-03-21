# -*- coding: utf-8 -*-

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
