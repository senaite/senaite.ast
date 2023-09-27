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
# Copyright 2020-2023 by it's authors.
# Some rights reserved, see README and LICENSE.

from senaite.core.browser.form.adapters import EditFormAdapterBase

METHOD_FIELDS = (
    "form.widgets.IASTPanelBehavior.method"
    "form.widgets.IASTPanelBehavior.method:list"
)

DIFFUSION_DISK_FIELDS = (
    "form.widgets.IASTPanelBehavior.disk_content",
    "form.widgets.IASTPanelBehavior.disk_content:list"
    "form.widgets.IASTPanelBehavior.zone_size",
    "form.widgets.IASTPanelBehavior.zone_size:list"
)

METHOD_DIFFUSION_DISK = "diffusion_disk"


class ASTPanelEditForm(EditFormAdapterBase):
    """Edit form for ASTPanel content type
    """

    def initialized(self, data):
        form = data.get("form")
        method = form.get(METHOD_FIELDS[1])
        self.toggle_method(method)
        return self.data

    def modified(self, data):
        if data.get("name") in METHOD_FIELDS:
            method = data.get("value")
            self.toggle_method(method)
        return self.data

    def toggle_method(self, method):
        """Shows/hides fields that depend on the method of choice
        """
        if not isinstance(method, list):
            method = [method]
        if METHOD_DIFFUSION_DISK in method:
            # Show fields for diffusion disk
            map(self.add_show_field, DIFFUSION_DISK_FIELDS)
        else:
            map(self.add_hide_field, DIFFUSION_DISK_FIELDS)
