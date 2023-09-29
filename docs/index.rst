senaite.ast
===========

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

Resistance analyses are qualitative and the supported results are in accordance
with the `new definitions of susceptibility testing categories by EUCAST 2019`_:

- S: Susceptible, standard dosing regimen
- I: Susceptible, increased exposure
- R: Resistant

Although user can configure AST Panels for the automatic addition of analyses
for the capture of diameter of the zone of inhibition, the system does not
automatically calculate the qualitative results based on the diameter of zone
and the minimum inhibitory concentrations (MICs). However, system can infere
the susceptibility testing category automatically based on pre-defined
Breakpoints Tables, along with the diameter of the inhibitory zone or the MIC
value.

Once installed, this add-on allows the laboratory to:

* Maintain microorganisms (via `senaite.microorganism`_)
* Maintain antibiotics and antibiotic classes (via `senaite.abx`_)
* Maintain pre-defined AST Panels
* Maintain pre-defined Breakpoints Tables
* Analysis for the identification of microorganisms
* Assignment of pre-defined AST Panels to a sample
* Sample-level customization of AST Panel
* Selective reporting of resistance results
* Support for and selective reporting of extrapolated antibiotics

This documentation is divided in different parts. We recommend that you get
started with :doc:`installation` and then head over to the :doc:`quickstart`.

Table of Contents:

.. toctree::
   :maxdepth: 2

   installation
   quickstart
   changelog
   license


.. Links

.. _SENAITE LIMS: https://www.senaite.com
.. _senaite.ast: https://pypi.org/project/senaite.ast
.. _new definitions of susceptibility testing categories by EUCAST 2019: https://www.eucast.org/newsiandr/
.. _senaite.microorganism: https://pypi.org/project/senaite.microorganism
.. _senaite.abx: https://pypi.org/project/senaite.abx
