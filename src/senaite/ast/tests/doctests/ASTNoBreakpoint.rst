Submission of AST analyses without a breakpoint
-----------------------------------------------

The sensitivity category (S/I/R) of an antibiotic is inferred from the
breakpoint defined for the microorganism the analysis is associated to. When
the antibiotic has no breakpoint for that microorganism no category can be
inferred, and the analysis has to remain submittable nonetheless.

Running this test from the buildout directory:

    bin/test test_textual_doctests -t ASTNoBreakpoint


Test Setup
..........

Needed Imports:

    >>> from bika.lims import api
    >>> from bika.lims.api.analysis import is_result_complete
    >>> from bika.lims.utils.analysisrequest import create_analysisrequest
    >>> from bika.lims.workflow import doActionFor as do_action_for
    >>> from bika.lims.workflow import isTransitionAllowed
    >>> from DateTime import DateTime
    >>> from plone.app.testing import setRoles
    >>> from plone.app.testing import TEST_USER_ID
    >>> from senaite.ast.config import BREAKPOINTS_TABLE_KEY
    >>> from senaite.ast.config import RESISTANCE_KEY
    >>> from senaite.ast.config import ZONE_SIZE_KEY
    >>> from senaite.ast.utils import create_ast_analyses
    >>> from senaite.ast.utils import get_ast_group

Variables:

    >>> portal = self.portal
    >>> request = self.request
    >>> bika_setup = portal.bika_setup
    >>> date_now = DateTime().strftime("%Y-%m-%d")

Functional Helpers:

    >>> def new_sample(services):
    ...     values = {
    ...         "Client": client.UID(),
    ...         "Contact": contact.UID(),
    ...         "DateSampled": date_now,
    ...         "SampleType": sampletype.UID()}
    ...     service_uids = map(api.get_uid, services)
    ...     sample = create_analysisrequest(client, request, values, service_uids)
    ...     transitioned = do_action_for(sample, "receive")
    ...     return sample

    >>> def get_interim(analysis, keyword):
    ...     interims = analysis.getInterimFields()
    ...     interims = filter(lambda i: i["keyword"] == keyword, interims)
    ...     return interims[0] if interims else None

    >>> def set_zone_sizes(analysis, size):
    ...     interims = analysis.getInterimFields()
    ...     for interim in interims:
    ...         interim["value"] = size
    ...     analysis.setInterimFields(interims)

We need to create some basic objects for the test:

    >>> setRoles(portal, TEST_USER_ID, ["LabManager"])
    >>> client = api.create(portal.clients, "Client", Name="Happy Hills", ClientID="HH")
    >>> contact = api.create(client, "Contact", Firstname="Rita", Lastname="Mohale")
    >>> sampletype = api.create(portal.setup.sampletypes, "SampleType", title="Blood", Prefix="BL")
    >>> labcontact = api.create(bika_setup.bika_labcontacts, "LabContact", Firstname="Lab", Lastname="Manager")
    >>> department = api.create(portal.setup.departments, "Department", title="Microbiology", Manager=labcontact)
    >>> category = api.create(portal.setup.analysiscategories, "AnalysisCategory", title="Microbiology", Department=department)
    >>> gram = api.create(bika_setup.bika_analysisservices, "AnalysisService", title="GRAM", Keyword="GRAM", Category=category.UID())

Create a microorganism and two antibiotics, and a breakpoints table with a
breakpoint for the first antibiotic only:

    >>> ecoli = api.create(bika_setup.microorganisms, "Microorganism", title="Escherichia coli")
    >>> amx = api.create(bika_setup.antibiotics, "Antibiotic", title="Amoxicillin", abbreviation="AMX")
    >>> cip = api.create(bika_setup.antibiotics, "Antibiotic", title="Ciprofloxacin", abbreviation="CIP")
    >>> bp_table = api.create(bika_setup.astbreakpoints, "BreakpointsTable", title="EUCAST")
    >>> bp_table.breakpoints = [
    ...     {"antibiotic": api.get_uid(amx),
    ...      "microorganism": api.get_uid(ecoli),
    ...      "diameter_s": 14, "diameter_r": 14,
    ...      "disk_content": 10,
    ...      "mic_s": 0.0, "mic_r": 0.0},
    ... ]


Antibiotic without a breakpoint for the microorganism
.....................................................

Create the AST analyses for both antibiotics:

    >>> sample = new_sample([gram])
    >>> keywords = [ZONE_SIZE_KEY, BREAKPOINTS_TABLE_KEY, RESISTANCE_KEY]
    >>> ast_analyses = create_ast_analyses(sample, keywords, ecoli, [amx, cip])
    >>> group = get_ast_group(ast_analyses[0])

Only one breakpoints table suits the first antibiotic, while for the second
one the only choice available is `N/S` (not selected), stored as `0`:

    >>> breakpoints = group[BREAKPOINTS_TABLE_KEY]
    >>> get_interim(breakpoints, "AMX").get("choices") == "0:N/S|{}:EUCAST".format(api.get_uid(bp_table))
    True

    >>> get_interim(breakpoints, "CIP").get("choices")
    '0:N/S'

    >>> get_interim(breakpoints, "CIP").get("value")
    '0'

Select the breakpoints table for the antibiotic that has one:

    >>> interims = breakpoints.getInterimFields()
    >>> for interim in interims:
    ...     if interim["keyword"] == "AMX":
    ...         interim["value"] = api.get_uid(bp_table)
    >>> breakpoints.setInterimFields(interims)

Enter the zone diameters for both antibiotics and run the calculation:

    >>> zone = group[ZONE_SIZE_KEY]
    >>> set_zone_sizes(zone, "20")
    >>> zone.calculateResult(override=True)
    True

A sensitivity category is inferred for the antibiotic with a breakpoint, and
its result variable does not allow empty values:

    >>> sensitivity = group[RESISTANCE_KEY]
    >>> get_interim(sensitivity, "AMX").get("value")
    '1'

    >>> get_interim(sensitivity, "AMX").get("allow_empty")
    False

No category can be inferred for the antibiotic without a breakpoint, so the
choice with no category (`0`) is assigned and empty values are allowed:

    >>> get_interim(sensitivity, "CIP").get("value")
    '0'

    >>> get_interim(sensitivity, "CIP").get("allow_empty")
    True

Therefore the analysis can be submitted:

    >>> is_result_complete(sensitivity)
    True

    >>> isTransitionAllowed(sensitivity, "submit")
    True

    >>> transitioned = do_action_for(sensitivity, "submit")
    >>> api.get_workflow_status_of(sensitivity)
    'to_be_verified'

And so can the analyses for the zone diameters and the breakpoints tables:

    >>> transitioned = do_action_for(breakpoints, "submit")
    >>> api.get_workflow_status_of(breakpoints)
    'to_be_verified'

    >>> transitioned = do_action_for(zone, "submit")
    >>> api.get_workflow_status_of(zone)
    'to_be_verified'


No sensitivity category for any of the antibiotics
..................................................

The result of the sensitivity category analysis is a list with the categories
to report, that is empty when no category could be inferred at all. An empty
list is an empty result, so the "nothing to report" result is stored instead
and the analysis remains submittable:

    >>> sample = new_sample([gram])
    >>> ast_analyses = create_ast_analyses(sample, keywords, ecoli, [cip])
    >>> group = get_ast_group(ast_analyses[0])
    >>> zone = group[ZONE_SIZE_KEY]
    >>> set_zone_sizes(zone, "20")
    >>> zone.calculateResult(override=True)
    True

    >>> sensitivity = group[RESISTANCE_KEY]
    >>> get_interim(sensitivity, "CIP").get("value")
    '0'

    >>> sensitivity.getResult()
    '-'

    >>> is_result_complete(sensitivity)
    True

    >>> transitioned = do_action_for(sensitivity, "submit")
    >>> api.get_workflow_status_of(sensitivity)
    'to_be_verified'


A missing zone diameter is still required
.........................................

Empty values are only allowed for the sensitivity category, and only because
no breakpoint is available. As long as no zone diameter is entered, no
category is assigned and the analysis cannot be submitted:

    >>> sample = new_sample([gram])
    >>> ast_analyses = create_ast_analyses(sample, keywords, ecoli, [cip])
    >>> group = get_ast_group(ast_analyses[0])
    >>> sensitivity = group[RESISTANCE_KEY]
    >>> get_interim(sensitivity, "CIP").get("value")
    ''

    >>> get_interim(sensitivity, "CIP").get("allow_empty")

    >>> isTransitionAllowed(sensitivity, "submit")
    False

    >>> zone = group[ZONE_SIZE_KEY]
    >>> isTransitionAllowed(zone, "submit")
    False
