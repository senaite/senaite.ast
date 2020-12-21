Antibiotic Sensitivity Testing (AST) for SENAITE
================================================

.. image:: https://img.shields.io/pypi/v/senaite.ast.svg?style=flat-square
    :target: https://pypi.python.org/pypi/senaite.ast

.. image:: https://img.shields.io/travis/senaite/senaite.ast/master.svg?style=flat-square
    :target: https://travis-ci.org/senaite/senaite.ast

.. image:: https://readthedocs.org/projects/pip/badge/
    :target: https://senaiteast.readthedocs.org

.. image:: https://img.shields.io/github/issues-pr/senaite/senaite.ast.svg?style=flat-square
    :target: https://github.com/senaite/senaite.ast/pulls

.. image:: https://img.shields.io/github/issues/senaite/senaite.ast.svg?style=flat-square
    :target: https://github.com/senaite/senaite.ast/issues

.. image:: https://img.shields.io/badge/Made%20for%20SENAITE-%E2%AC%A1-lightgrey.svg
   :target: https://www.senaite.com


About
-----

This add-on enables Antibiotic Sensitivity Testing (AST) for `SENAITE LIMS`_ by
allowing the user to add analyses to a sample that are specifically designed for
the measurement of the susceptibility of microorganisms to antibiotics. These
analyses can be added either by means of pre-defined AST Panels or by direct
assignment of Antibiotics and Microorganisms through a matrix.

`senaite.ast`_ also incorporates a default analysis for the identification of
microorganisms present in a given sample. Once microorganisms are identified by
means of this identification analysis, the system automatically populates the
list of available AST Panels for selection with those that fit better with the
identified microorganism(s).

Resistance analyses are qualitative and the supported results are: [R]esistant,
[S]ensible, [+] positive and [-] negative. Although user can configure AST
Panels for the automatic addition of analyses for the capture of diameter of
the zone of inhibition, the system does not automatically calculate the
qualitative results based on the diameter of zone and the minimum inhibitory
concentrations (MICs).

Once installed, this add-on allows the laboratory to:

* Maintain microorganisms (via `senaite.microorganism`_)
* Maintain antibiotics and antibiotic classes (via `senaite.abx`_)
* Maintain pre-defined AST Panels
* Analysis for the identification of microorganisms
* Assignment of pre-defined AST Panels to a sample
* Sample-level customization of AST Panel
* Selective reporting of resistance results


Documentation
-------------

* https://senaiteast.readthedocs.io


Contribute
----------

We want contributing to SENAITE.AST to be fun, enjoyable, and educational
for anyone, and everyone. This project adheres to the `Contributor Covenant`_.

By participating, you are expected to uphold this code. Please report
unacceptable behavior.

Contributions go far beyond pull requests and commits. Although we love giving
you the opportunity to put your stamp on SENAITE.AST, we also are thrilled
to receive a variety of other contributions.

Please, read `Contributing to senaite.ast document`_.

If you wish to contribute with translations, check the project site on `Transifex`_.


License
-------

**SENAITE.AST** Copyright (C) 2020 RIDING BYTES & NARALABS

This program is free software; you can redistribute it and/or modify it under
the terms of the `GNU General Public License version 2`_ as published
by the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.


.. Links

.. _SENAITE LIMS: https://www.senaite.com
.. _senaite.ast: https://pypi.org/project/senaite.ast
.. _senaite.microorganism: https://pypi.org/project/senaite.microorganism
.. _senaite.abx: https://pypi.org/project/senaite.abx
.. _Contributor Covenant: https://github.com/senaite/senaite.ast/blob/master/CODE_OF_CONDUCT.md
.. _Contributing to senaite.ast document: https://github.com/senaite/senaite.ast/blob/master/CONTRIBUTING.md
.. _Transifex: https://www.transifex.com/senaite/senaite-ast
.. _Community site: https://community.senaite.org/
.. _Gitter channel: https://gitter.im/senaite/Lobby
.. _Users list: https://sourceforge.net/projects/senaite/lists/senaite-users
.. _GNU General Public License version 2: https://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

