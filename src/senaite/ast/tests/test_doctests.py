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

import doctest
from os.path import join

from pkg_resources import resource_listdir

import unittest2 as unittest
from senaite.ast import PRODUCT_NAME
from senaite.ast.tests.base import SimpleTestCase
from Testing import ZopeTestCase as ztc

# Option flags for doctests
flags = doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE | doctest.REPORT_NDIFF


def test_suite():
    suite = unittest.TestSuite()
    for doctestfile in get_doctest_files():
        suite.addTests([
            ztc.ZopeDocFileSuite(
                doctestfile,
                test_class=SimpleTestCase,
                optionflags=flags
            )
        ])
    return suite


def get_doctest_files():
    """Returns a list with the doctest files
    """
    files = resource_listdir(PRODUCT_NAME, "tests/doctests")
    files = filter(lambda file_name: file_name.endswith(".rst"), files)
    return map(lambda file_name: join("doctests", file_name), files)
