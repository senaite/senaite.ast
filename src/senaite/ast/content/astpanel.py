from bika.lims.catalog import SETUP_CATALOG
from plone.dexterity.content import Container
from plone.supermodel import model
from zope.interface import implementer


class IASTPanel(model.Schema):
    """AST Panel content interface
    """
    pass


@implementer(IASTPanel)
class ASTPanel(Container):
    """AST Panel content
    """
    # Catalogs where this type will be catalogued
    _catalogs = [SETUP_CATALOG]
