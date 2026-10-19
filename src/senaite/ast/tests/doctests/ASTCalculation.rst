AST Calculation
---------------

This test verifies that the AST calculation created during setup is
correctly linked to AST analyses and that the sensitivity testing
categories (R/I/S) are computed when zone diameter results are saved.

Running this test from the buildout directory:

    bin/test test_textual_doctests -t ASTCalculation


Test Setup
..........

Needed Imports:

    >>> from DateTime import DateTime
    >>> from bika.lims import api
    >>> from bika.lims.utils.analysisrequest import create_analysisrequest
    >>> from bika.lims.workflow import doActionFor as do_action_for
    >>> from plone.app.testing import setRoles
    >>> from plone.app.testing import TEST_USER_ID

    >>> from senaite.ast.config import AST_CALCULATION_TITLE
    >>> from senaite.ast.config import BREAKPOINTS_TABLE_KEY
    >>> from senaite.ast.config import RESISTANCE_KEY
    >>> from senaite.ast.config import ZONE_SIZE_KEY
    >>> from senaite.ast.utils import create_ast_analyses
    >>> from senaite.ast.utils import get_ast_group
    >>> from senaite.ast.utils import get_service

Variables:

    >>> portal = self.portal
    >>> request = self.request
    >>> bika_setup = api.get_setup()
    >>> senaite_setup = api.get_senaite_setup()
    >>> date_now = DateTime().strftime("%Y-%m-%d")
    >>> setRoles(portal, TEST_USER_ID, ["LabManager"])


Verify AST calculation exists
.............................

The AST calculation is created automatically when `senaite.ast` is
installed.  It must live in the DX calculations folder:

    >>> calc_folder = senaite_setup.calculations
    >>> calcs = [c for c in calc_folder.objectValues()
    ...          if api.get_title(c) == AST_CALCULATION_TITLE]
    >>> len(calcs)
    1

    >>> calculation = calcs[0]
    >>> calculation.getFormula()
    'calc_ast(%(context_uid)s)'
    >>> calculation.getPythonImports()
    [{'function': 'calc_ast', 'module': 'senaite.ast.calc'}]


Create test data
................

Create the basic objects needed for a sample:

    >>> client = api.create(portal.clients, "Client",
    ...     Name="Test Client", ClientID="TC")
    >>> contact = api.create(client, "Contact",
    ...     Firstname="Jane", Lastname="Doe")
    >>> sampletype = api.create(portal.setup.sampletypes, "SampleType",
    ...     title="Blood", Prefix="BL")
    >>> labcontact = api.create(bika_setup.bika_labcontacts, "LabContact",
    ...     Firstname="Lab", Lastname="Manager")
    >>> department = api.create(portal.setup.departments, "Department",
    ...     title="Microbiology", Manager=labcontact)
    >>> category = api.create(portal.setup.analysiscategories,
    ...     "AnalysisCategory", title="Micro", Department=department)

Create a regular analysis service for the sample (a sample needs at least
one non-AST analysis):

    >>> gram = api.create(bika_setup.bika_analysisservices, "AnalysisService",
    ...     title="GRAM", Keyword="GRAM", Price="10", Category=category.UID())

Create a Microorganism:

    >>> mo_folder = bika_setup.microorganisms
    >>> ecoli = api.create(mo_folder, "Microorganism", title="Escherichia coli")

Create two Antibiotics:

    >>> abx_folder = bika_setup.antibiotics
    >>> amx = api.create(abx_folder, "Antibiotic",
    ...     title="Amoxicillin", abbreviation="AMX")
    >>> cip = api.create(abx_folder, "Antibiotic",
    ...     title="Ciprofloxacin", abbreviation="CIP")

Create a Breakpoints Table with breakpoint entries for each antibiotic and
microorganism.  Zone diameter breakpoints are:

- Amoxicillin: S >= 14 mm, R < 14 mm (no I range)
- Ciprofloxacin: S >= 25 mm, R < 22 mm (I range between 22 and 24 mm)

    >>> bp_folder = bika_setup.astbreakpoints
    >>> bp_table = api.create(bp_folder, "BreakpointsTable",
    ...     title="EUCAST 2025")
    >>> bp_table.breakpoints = [
    ...     {"antibiotic": api.get_uid(amx),
    ...      "microorganism": api.get_uid(ecoli),
    ...      "diameter_s": 14, "diameter_r": 14,
    ...      "disk_content": 10,
    ...      "mic_s": 0.0, "mic_r": 0.0},
    ...     {"antibiotic": api.get_uid(cip),
    ...      "microorganism": api.get_uid(ecoli),
    ...      "diameter_s": 25, "diameter_r": 22,
    ...      "disk_content": 5,
    ...      "mic_s": 0.0, "mic_r": 0.0},
    ... ]


Verify calculation is linked to AST services
.............................................

All AST services with a calculation setting should have the AST calculation
assigned:

    >>> zone_service = get_service(ZONE_SIZE_KEY)
    >>> zone_calc = zone_service.getCalculation()
    >>> zone_calc is not None
    True
    >>> api.get_title(zone_calc) == AST_CALCULATION_TITLE
    True

    >>> resistance_service = get_service(RESISTANCE_KEY)
    >>> res_calc = resistance_service.getCalculation()
    >>> api.get_title(res_calc) == AST_CALCULATION_TITLE
    True


Create a sample with AST analyses
..................................

Create a sample with the basic analysis service:

    >>> values = {
    ...     "Client": client.UID(),
    ...     "Contact": contact.UID(),
    ...     "DateSampled": date_now,
    ...     "SampleType": sampletype.UID()}
    >>> sample = create_analysisrequest(
    ...     client, request, values, [api.get_uid(gram)])

Receive the sample:

    >>> transitioned = do_action_for(sample, "receive")
    >>> api.get_workflow_status_of(sample)
    'sample_received'

Create AST analyses for zone size, breakpoints selection, and sensitivity
category for the microorganism with the two antibiotics:

    >>> antibiotics = [amx, cip]
    >>> keywords = [ZONE_SIZE_KEY, BREAKPOINTS_TABLE_KEY, RESISTANCE_KEY]
    >>> ast_analyses = create_ast_analyses(
    ...     sample, keywords, ecoli, antibiotics)
    >>> len(ast_analyses)
    3

AST analyses are marked as scientific names so their microorganism labels and
results use scientific-name formatting in reports:

    >>> all(analysis.getScientificName() for analysis in ast_analyses)
    True


Verify formula is snapshotted onto analyses
............................................

Each AST analysis must have the formula and python imports snapshotted from
the calculation (this is the core change from PR #2600 — analyses no longer
look up the live Calculation object at eval time):

    >>> zone_an = [a for a in ast_analyses if a.getKeyword() == ZONE_SIZE_KEY][0]
    >>> zone_an.getCalculationFormula()
    'calc_ast(%(context_uid)s)'
    >>> zone_an.getCalculationImports()
    [{u'function': u'calc_ast', u'module': u'senaite.ast.calc'}]


Set breakpoints and zone sizes
..............................

Get the AST group to access the analyses by keyword:

    >>> group = get_ast_group(zone_an)

Set the breakpoints table for both antibiotics.  Each antibiotic is stored
as an interim field, and the value is the UID of the breakpoints table:

    >>> bp_uid = api.get_uid(bp_table)
    >>> bp_analysis = group[BREAKPOINTS_TABLE_KEY]
    >>> bp_interims = bp_analysis.getInterimFields()
    >>> for interim in bp_interims:
    ...     interim["value"] = bp_uid
    >>> bp_analysis.setInterimFields(bp_interims)

Set zone diameter results:

- Amoxicillin: 20 mm (should be S, since >= 14)
- Ciprofloxacin: 23 mm (should be I, since >= 22 and < 25)

    >>> zone_interims = zone_an.getInterimFields()
    >>> for interim in zone_interims:
    ...     if interim["keyword"] == "AMX":
    ...         interim["value"] = "20"
    ...     elif interim["keyword"] == "CIP":
    ...         interim["value"] = "23"
    >>> zone_an.setInterimFields(zone_interims)


Trigger calculation
...................

Call `calculateResult` on the zone size analysis.  This executes the
snapshotted formula `calc_ast(%(context_uid)s)`, which resolves the python
import `senaite.ast.calc:calc_ast` and runs the full AST calculation
pipeline:

    >>> zone_an.calculateResult(override=True)
    True

The sensitivity category analysis should now have the computed R/I/S values
for each antibiotic:

    >>> sensitivity = group[RESISTANCE_KEY]
    >>> sens_interims = sensitivity.getInterimFields()

Build a mapping of antibiotic abbreviation to sensitivity value for
verification:

    >>> results = dict((i["keyword"], i["value"]) for i in sens_interims)

Amoxicillin with 20 mm zone diameter is **Susceptible** (S >= 14):

    >>> results["AMX"]
    '1'

The value ``'1'`` corresponds to choice ``S`` in the predefined choices
``"0:|1:S|2:I|3:R"``:

    >>> from senaite.ast.utils import get_sensitivity_category_value
    >>> get_sensitivity_category_value("S")
    '1'

Ciprofloxacin with 23 mm zone diameter is **Susceptible at increased
exposure** (22 <= zone < 25):

    >>> results["CIP"]
    '2'

    >>> get_sensitivity_category_value("I")
    '2'


Recalculate with different zone sizes
......................................

Change the Ciprofloxacin zone diameter to 10 mm (should be R, since < 22):

    >>> zone_interims = zone_an.getInterimFields()
    >>> for interim in zone_interims:
    ...     if interim["keyword"] == "CIP":
    ...         interim["value"] = "10"
    >>> zone_an.setInterimFields(zone_interims)

    >>> zone_an.calculateResult(override=True)
    True

    >>> sens_interims = sensitivity.getInterimFields()
    >>> results = dict((i["keyword"], i["value"]) for i in sens_interims)
    >>> results["CIP"]
    '3'

    >>> get_sensitivity_category_value("R")
    '3'

Amoxicillin remains Susceptible (zone size was not changed):

    >>> results["AMX"]
    '1'
