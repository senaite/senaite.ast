import collections

from bika.lims import _ as _c
from bika.lims import api
from bika.lims.catalog import SETUP_CATALOG
from bika.lims.utils import get_link_for
from plone.memoize import view
from senaite.app.listing import ListingView
from senaite.ast import messageFactory as _


class ASTPanelFolderView(ListingView):
    """AST Panels listing view
    """

    def __init__(self, context, request):
        super(ASTPanelFolderView, self).__init__(context, request)

        self.catalog = SETUP_CATALOG

        self.contentFilter = {
            "portal_type": "ASTPanel",
            "sort_on": "sortable_title",
            "sort_order": "ascending",
        }

        self.context_actions = {
            _c("Add"): {
                "url": "++add++ASTPanel",
                "icon": "add.png"}
            }

        self.show_select_column = True

        self.columns = collections.OrderedDict((
            ("Title", {
                "title": _c("Title"),
                "index": "sortable_title"
            }),
            ("Description", {
                "title": _("Description"),
                "index": "Description"
            }),
        ))

        self.review_states = [
            {
                "id": "default",
                "title": _c("Active"),
                "contentFilter": {"is_active": True},
                "transitions": [],
                "columns": self.columns.keys(),
            }, {
                "id": "inactive",
                "title": _c("Inactive"),
                "contentFilter": {'is_active': False},
                "transitions": [],
                "columns": self.columns.keys(),
            }, {
                "id": "all",
                "title": _c("All"),
                "contentFilter": {},
                "columns": self.columns.keys(),
            },
        ]

    def update(self):
        """Update hook
        """
        super(ASTPanelFolderView, self).update()

    def before_render(self):
        """Before template render hook
        """
        super(ASTPanelFolderView, self).before_render()

    def folderitem(self, obj, item, index):
        """Service triggered each time an item is iterated in folderitems.
        The use of this service prevents the extra-loops in child objects.
        :obj: the instance of the class to be foldered
        :item: dict containing the properties of the object to be used by
            the template
        :index: current index of the item
        """
        item["replace"]["Title"] = get_link_for(obj)
        return item

    def get_children_hook(self, parent_uid, child_uids=None):
        """Hook to get the children of an item
        """
        super(ASTPanelFolderView, self).get_children_hook(
            parent_uid, child_uids=child_uids)
