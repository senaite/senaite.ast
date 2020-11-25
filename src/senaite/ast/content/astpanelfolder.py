from plone.dexterity.content import Container
from plone.supermodel import model
from senaite.core.interfaces import IHideActionsMenu
from zope.interface import implementer


class IASTPanelFolder(model.Schema):
    """AST Panel folder interface
    """
    # Implements IBasic behavior (title + description)
    pass


@implementer(IASTPanelFolder, IHideActionsMenu)
class ASTPanelFolder(Container):
    """AST Panel folder
    """
    pass
