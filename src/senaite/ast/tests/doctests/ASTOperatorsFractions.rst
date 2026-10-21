AST Operators and Fractions
---------------------------

This test verifies that zone diameter and MIC results support comparison
operators (``<``, ``>``, ``<=``, ``>=``) and fractions (e.g. ``1/2``),
and that the automatic sensitivity category calculation (R/I/S) behaves
correctly:

- **Plain numbers and fractions**: sensitivity category is calculated
  automatically from the breakpoints table.
- **Values with operators**: the value is a boundary and not an exact
  measure, so the category is only calculated when it is the same for the
  whole range the operator stands for. It is left for the user to set
  otherwise, and the antibiotic allows an empty category meanwhile, so the
  results can be submitted either way.

Running this test from the buildout directory:

    bin/test test_textual_doctests -t ASTOperatorsFractions


Test Setup
..........

Needed Imports:

    >>> from DateTime import DateTime
    >>> from bika.lims import api
    >>> from bika.lims.utils.analysisrequest import create_analysisrequest
    >>> from bika.lims.workflow import doActionFor as do_action_for
    >>> from bika.lims.workflow import getAllowedTransitions
    >>> from plone.app.testing import setRoles
    >>> from plone.app.testing import TEST_USER_ID

    >>> from senaite.ast.calc import resolve_fraction
    >>> from senaite.ast.config import BREAKPOINTS_TABLE_KEY
    >>> from senaite.ast.config import MIC_KEY
    >>> from senaite.ast.config import RESISTANCE_KEY
    >>> from senaite.ast.config import ZONE_SIZE_KEY
    >>> from senaite.ast.utils import create_ast_analyses
    >>> from senaite.ast.utils import get_ast_group
    >>> from senaite.ast.utils import get_sensitivity_category
    >>> from senaite.ast.utils import get_sensitivity_category_value
    >>> from senaite.ast.utils import split_operator

Variables:

    >>> portal = self.portal
    >>> request = self.request
    >>> bika_setup = api.get_setup()
    >>> senaite_setup = api.get_senaite_setup()
    >>> date_now = DateTime().strftime("%Y-%m-%d")
    >>> setRoles(portal, TEST_USER_ID, ["LabManager"])


resolve_fraction helper
.......................

Plain numbers pass through unchanged:

    >>> resolve_fraction("20")
    '20'

    >>> resolve_fraction("0.5")
    '0.5'

Fractions are resolved to their float equivalent:

    >>> resolve_fraction("1/2")
    0.5

    >>> resolve_fraction("3/4")
    0.75

    >>> resolve_fraction("13/4")
    3.25

Values with operators are returned as-is (not resolvable):

    >>> resolve_fraction(">20")
    '>20'

    >>> resolve_fraction("<=0.5")
    '<=0.5'

Operator combined with fraction is returned as-is (numerator is not
floatable):

    >>> resolve_fraction(">1/2")
    '>1/2'

Edge cases:

    >>> resolve_fraction("")
    ''

    >>> resolve_fraction(None)
    ''

    >>> resolve_fraction("1/0")
    '1/0'

    >>> resolve_fraction("1/-2")
    '1/-2'


split_operator helper
.....................

Values without an operator are returned unchanged:

    >>> split_operator("20")
    ('', '20')

    >>> split_operator("1/2")
    ('', '1/2')

The supported operators are split off the value:

    >>> split_operator(">20")
    ('>', '20')

    >>> split_operator(">=20")
    ('>=', '20')

    >>> split_operator("<0.25")
    ('<', '0.25')

    >>> split_operator("<=1/2")
    ('<=', '1/2')

Surrounding whitespace is discarded:

    >>> split_operator("  >=  20  ")
    ('>=', '20')

Values that are not strings are returned as they come:

    >>> split_operator(None)
    ('', None)

    >>> split_operator(14.5)
    ('', 14.5)


Sensitivity category of a boundary value
........................................

A value with an operator stands for a range rather than for a measure, so
its category is only inferred when the whole range falls into the same one.
With zone diameter breakpoints of S >= 25 mm and R < 22 mm:

    >>> breakpoint = {"diameter_s": 25, "diameter_r": 22,
    ...               "mic_s": 0.25, "mic_r": 0.5}

A diameter of at least 25 mm is susceptible, whatever its exact value:

    >>> get_sensitivity_category(25, breakpoint, ZONE_SIZE_KEY,
    ...                          operator=">=", default="")
    'S'

The resistant range leaves its own threshold out (R is `value < 22`), just
as a strict operator leaves the boundary out, so "< 22" is resistant:

    >>> get_sensitivity_category(22, breakpoint, ZONE_SIZE_KEY,
    ...                          operator="<", default="")
    'R'

"<= 22" includes the 22 mm itself, which is already intermediate:

    >>> get_sensitivity_category(22, breakpoint, ZONE_SIZE_KEY,
    ...                          operator="<=", default="")
    ''

A range that spans more than one category cannot be inferred either. Above
23 mm the diameter can be both intermediate and susceptible:

    >>> get_sensitivity_category(23, breakpoint, ZONE_SIZE_KEY,
    ...                          operator=">", default="")
    ''

MIC values read the other way round, the lower the more susceptible. Here
S <= 0.25 and R > 0.5:

    >>> get_sensitivity_category(0.25, breakpoint, MIC_KEY,
    ...                          operator="<=", default="")
    'S'

    >>> get_sensitivity_category(0.5, breakpoint, MIC_KEY,
    ...                          operator=">", default="")
    'R'

    >>> get_sensitivity_category(0.25, breakpoint, MIC_KEY,
    ...                          operator=">", default="")
    ''

Without a breakpoint there is no category to infer, operator or not:

    >>> get_sensitivity_category(20, None, ZONE_SIZE_KEY,
    ...                          operator=">=", default="")
    ''


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

Create a regular analysis service (a sample needs at least one non-AST
analysis):

    >>> gram = api.create(bika_setup.bika_analysisservices, "AnalysisService",
    ...     title="GRAM", Keyword="GRAM", Price="10", Category=category.UID())

Create a Microorganism:

    >>> mo_folder = bika_setup.microorganisms
    >>> ecoli = api.create(mo_folder, "Microorganism",
    ...     title="Escherichia coli")

Create three Antibiotics:

    >>> abx_folder = bika_setup.antibiotics
    >>> amx = api.create(abx_folder, "Antibiotic",
    ...     title="Amoxicillin", abbreviation="AMX")
    >>> cip = api.create(abx_folder, "Antibiotic",
    ...     title="Ciprofloxacin", abbreviation="CIP")
    >>> gen = api.create(abx_folder, "Antibiotic",
    ...     title="Gentamicin", abbreviation="GEN")

Create a Breakpoints Table.  Zone diameter breakpoints are:

- Amoxicillin: S >= 14 mm, R < 14 mm (no I range)
- Ciprofloxacin: S >= 25 mm, R < 22 mm (I range between 22 and 24 mm)
- Gentamicin: S >= 17 mm, R < 14 mm (I range between 14 and 16 mm)

MIC breakpoints are:

- Amoxicillin: S <= 8, R > 8 (no I range)
- Ciprofloxacin: S <= 0.25, R > 0.5 (I range between 0.25 and 0.5)
- Gentamicin: S <= 2, R > 4 (I range between 2 and 4)

    >>> bp_folder = bika_setup.astbreakpoints
    >>> bp_table = api.create(bp_folder, "BreakpointsTable",
    ...     title="EUCAST 2025")
    >>> bp_table.breakpoints = [
    ...     {"antibiotic": api.get_uid(amx),
    ...      "microorganism": api.get_uid(ecoli),
    ...      "diameter_s": 14, "diameter_r": 14,
    ...      "disk_content": 10,
    ...      "mic_s": 8, "mic_r": 8},
    ...     {"antibiotic": api.get_uid(cip),
    ...      "microorganism": api.get_uid(ecoli),
    ...      "diameter_s": 25, "diameter_r": 22,
    ...      "disk_content": 5,
    ...      "mic_s": 0.25, "mic_r": 0.5},
    ...     {"antibiotic": api.get_uid(gen),
    ...      "microorganism": api.get_uid(ecoli),
    ...      "diameter_s": 17, "diameter_r": 14,
    ...      "disk_content": 10,
    ...      "mic_s": 2, "mic_r": 4},
    ... ]

Create a sample and receive it:

    >>> values = {
    ...     "Client": client.UID(),
    ...     "Contact": contact.UID(),
    ...     "DateSampled": date_now,
    ...     "SampleType": sampletype.UID()}
    >>> sample = create_analysisrequest(
    ...     client, request, values, [api.get_uid(gram)])
    >>> transitioned = do_action_for(sample, "receive")
    >>> api.get_workflow_status_of(sample)
    'sample_received'


Zone diameter with operators and fractions
..........................................

Create AST analyses for zone size, breakpoints selection, and sensitivity
category:

    >>> antibiotics = [amx, cip, gen]
    >>> keywords = [ZONE_SIZE_KEY, BREAKPOINTS_TABLE_KEY, RESISTANCE_KEY]
    >>> ast_analyses = create_ast_analyses(
    ...     sample, keywords, ecoli, antibiotics)

Get the AST group:

    >>> zone_an = [a for a in ast_analyses
    ...     if a.getKeyword() == ZONE_SIZE_KEY][0]
    >>> group = get_ast_group(zone_an)

Set the breakpoints table for all antibiotics:

    >>> bp_uid = api.get_uid(bp_table)
    >>> bp_analysis = group[BREAKPOINTS_TABLE_KEY]
    >>> bp_interims = bp_analysis.getInterimFields()
    >>> for interim in bp_interims:
    ...     interim["value"] = bp_uid
    >>> bp_analysis.setInterimFields(bp_interims)

Set zone diameter results with mixed input types:

- Amoxicillin: ``20`` mm (plain number, should calculate S >= 14)
- Ciprofloxacin: ``>23`` (operator spanning I and S, should NOT calculate)
- Gentamicin: ``29/2`` (fraction = 14.5, should calculate I: 14 <= 14.5 < 17)

    >>> zone_interims = zone_an.getInterimFields()
    >>> for interim in zone_interims:
    ...     if interim["keyword"] == "AMX":
    ...         interim["value"] = "20"
    ...     elif interim["keyword"] == "CIP":
    ...         interim["value"] = ">23"
    ...     elif interim["keyword"] == "GEN":
    ...         interim["value"] = "29/2"
    >>> zone_an.setInterimFields(zone_interims)

Trigger the calculation:

    >>> zone_an.calculateResult(override=True)
    True

Check the sensitivity categories:

    >>> sensitivity = group[RESISTANCE_KEY]
    >>> sens_interims = sensitivity.getInterimFields()
    >>> results = dict((i["keyword"], i["value"]) for i in sens_interims)

Amoxicillin with plain ``20`` mm is Susceptible (S >= 14):

    >>> results["AMX"] == get_sensitivity_category_value("S")
    True

Ciprofloxacin with operator ``>23`` covers both the intermediate range
(22 to 24 mm) and the susceptible one (>= 25 mm), so no category is
inferred and the result is left empty:

    >>> results["CIP"]
    ''

No category could be inferred for it, so the antibiotic allows an empty
value and the analysis can be submitted all the same:

    >>> cip = [i for i in sens_interims if i["keyword"] == "CIP"][0]
    >>> cip.get("allow_empty")
    True

    >>> "submit" in getAllowedTransitions(sensitivity)
    True

A category the user sets by hand for such an antibiotic is kept when the
results are saved again:

    >>> cip["value"] = get_sensitivity_category_value("R")
    >>> sensitivity.setInterimFields(sens_interims)
    >>> zone_an.calculateResult(override=True)
    True

    >>> sens_interims = sensitivity.getInterimFields()
    >>> cip = [i for i in sens_interims if i["keyword"] == "CIP"][0]
    >>> cip["value"] == get_sensitivity_category_value("R")
    True

Gentamicin with fraction ``29/2`` (= 14.5 mm) is Susceptible at increased
exposure (14 <= 14.5 < 17):

    >>> results["GEN"] == get_sensitivity_category_value("I")
    True


MIC with operators and fractions
................................

Create a new sample for MIC testing:

    >>> sample2 = create_analysisrequest(
    ...     client, request, values, [api.get_uid(gram)])
    >>> transitioned = do_action_for(sample2, "receive")

Create AST analyses for MIC:

    >>> keywords_mic = [MIC_KEY, BREAKPOINTS_TABLE_KEY, RESISTANCE_KEY]
    >>> ast_analyses_mic = create_ast_analyses(
    ...     sample2, keywords_mic, ecoli, antibiotics)

Get the AST group:

    >>> mic_an = [a for a in ast_analyses_mic
    ...     if a.getKeyword() == MIC_KEY][0]
    >>> group2 = get_ast_group(mic_an)

Set breakpoints table:

    >>> bp_analysis2 = group2[BREAKPOINTS_TABLE_KEY]
    >>> bp_interims2 = bp_analysis2.getInterimFields()
    >>> for interim in bp_interims2:
    ...     interim["value"] = bp_uid
    >>> bp_analysis2.setInterimFields(bp_interims2)

Set MIC results with mixed input types:

- Amoxicillin: ``1/2`` (fraction = 0.5, should calculate S <= 8)
- Ciprofloxacin: ``<=0.25`` (operator wholly within S, should calculate S)
- Gentamicin: ``3`` (plain number, should calculate I: 2 < 3 <= 4)

    >>> mic_interims = mic_an.getInterimFields()
    >>> for interim in mic_interims:
    ...     if interim["keyword"] == "AMX":
    ...         interim["value"] = "1/2"
    ...     elif interim["keyword"] == "CIP":
    ...         interim["value"] = "<=0.25"
    ...     elif interim["keyword"] == "GEN":
    ...         interim["value"] = "3"
    >>> mic_an.setInterimFields(mic_interims)

Trigger the calculation:

    >>> mic_an.calculateResult(override=True)
    True

Check the sensitivity categories:

    >>> sensitivity2 = group2[RESISTANCE_KEY]
    >>> sens_interims2 = sensitivity2.getInterimFields()
    >>> results2 = dict((i["keyword"], i["value"]) for i in sens_interims2)

Amoxicillin with fraction ``1/2`` (= 0.5) is Susceptible (S <= 8):

    >>> results2["AMX"] == get_sensitivity_category_value("S")
    True

Ciprofloxacin with operator ``<=0.25`` is Susceptible: the whole range the
operator stands for sits at or below the susceptible breakpoint (S <= 0.25):

    >>> results2["CIP"] == get_sensitivity_category_value("S")
    True

    >>> "submit" in getAllowedTransitions(sensitivity2)
    True

Gentamicin with plain ``3`` is Susceptible at increased exposure
(2 < 3 <= 4):

    >>> results2["GEN"] == get_sensitivity_category_value("I")
    True

A MIC that changes brings the category along with it. Raise the
Ciprofloxacin MIC above its resistant breakpoint (R > 0.5) and the category
inferred before is replaced:

    >>> mic_interims = mic_an.getInterimFields()
    >>> for interim in mic_interims:
    ...     if interim["keyword"] == "CIP":
    ...         interim["value"] = "1.0"
    >>> mic_an.setInterimFields(mic_interims)
    >>> mic_an.calculateResult(override=True)
    True

    >>> results2 = dict((i["keyword"], i["value"])
    ...     for i in sensitivity2.getInterimFields())
    >>> results2["CIP"] == get_sensitivity_category_value("R")
    True

    >>> cip2 = [i for i in sensitivity2.getInterimFields()
    ...     if i["keyword"] == "CIP"][0]
    >>> cip2.get("allow_empty")
    False


A category inferred before is not kept when it no longer applies
................................................................

An interim cannot tell a category the user set by hand from one a previous
calculation inferred. The first stands when the result becomes a boundary,
the second does not, because it no longer matches the result on display.

Create a new sample and enter a zone diameter Ciprofloxacin has a category
for (22 to 24 mm is the intermediate range):

    >>> sample3 = create_analysisrequest(
    ...     client, request, values, [api.get_uid(gram)])
    >>> transitioned = do_action_for(sample3, "receive")
    >>> ast_analyses3 = create_ast_analyses(
    ...     sample3, keywords, ecoli, antibiotics)
    >>> zone3 = [a for a in ast_analyses3
    ...     if a.getKeyword() == ZONE_SIZE_KEY][0]
    >>> group3 = get_ast_group(zone3)
    >>> bp3 = group3[BREAKPOINTS_TABLE_KEY]
    >>> interims = bp3.getInterimFields()
    >>> for interim in interims:
    ...     interim["value"] = bp_uid
    >>> bp3.setInterimFields(interims)

    >>> interims = zone3.getInterimFields()
    >>> for interim in interims:
    ...     if interim["keyword"] == "CIP":
    ...         interim["value"] = "23"
    >>> zone3.setInterimFields(interims)
    >>> zone3.calculateResult(override=True)
    True

The category is inferred, and the analysis does not allow it to be empty:

    >>> sensitivity3 = group3[RESISTANCE_KEY]
    >>> cip3 = [i for i in sensitivity3.getInterimFields()
    ...     if i["keyword"] == "CIP"][0]
    >>> cip3["value"] == get_sensitivity_category_value("I")
    True

    >>> cip3.get("allow_empty")
    False

Change the zone diameter to a boundary that spans more than one category.
The category cannot be inferred any longer, and the one inferred before is
cleared instead of being kept:

    >>> interims = zone3.getInterimFields()
    >>> for interim in interims:
    ...     if interim["keyword"] == "CIP":
    ...         interim["value"] = ">23"
    >>> zone3.setInterimFields(interims)
    >>> zone3.calculateResult(override=True)
    True

    >>> cip3 = [i for i in sensitivity3.getInterimFields()
    ...     if i["keyword"] == "CIP"][0]
    >>> cip3["value"] == get_sensitivity_category_value("")
    True

    >>> cip3.get("allow_empty")
    True


An antibiotic without a result still holds the submission back
..............................................................

Empty values are allowed while the result is a boundary, but the setting is
withdrawn as soon as the result is removed, so an antibiotic nobody entered
a result for keeps holding the submission back:

    >>> interims = zone3.getInterimFields()
    >>> for interim in interims:
    ...     if interim["keyword"] == "CIP":
    ...         interim["value"] = ""
    >>> zone3.setInterimFields(interims)
    >>> zone3.calculateResult(override=True)
    True

    >>> cip3 = [i for i in sensitivity3.getInterimFields()
    ...     if i["keyword"] == "CIP"][0]
    >>> cip3.get("allow_empty")
    False

    >>> "submit" in getAllowedTransitions(sensitivity3)
    False
