Submission of AST analyses without results
------------------------------------------

Multi-valued results, either from the result field or from a result variable
(interim), are stored as a JSON list with the selected values. An empty
selection is therefore stored as `"[]"`, and senaite.core does not allow the
submission of an analysis when its result, or the value of a result variable
that does not allow empty values, is empty.

This test verifies that AST analyses behave as expected in such circumstances.

Running this test from the buildout directory:

    bin/test test_textual_doctests -t ASTEmptyResults


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
    >>> from senaite.ast.config import IDENTIFICATION_KEY
    >>> from senaite.ast.config import REPORT_EXTRAPOLATED_KEY
    >>> from senaite.ast.config import RESISTANCE_KEY
    >>> from senaite.ast.utils import create_ast_analyses
    >>> from senaite.ast.utils import get_service

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

    >>> def set_interim_value(analysis, keyword, value):
    ...     interims = analysis.getInterimFields()
    ...     for interim in interims:
    ...         if interim["keyword"] == keyword:
    ...             interim["value"] = value
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

Create a Microorganism and two Antibiotics, where the second one is
extrapolated from the first:

    >>> ecoli = api.create(bika_setup.microorganisms, "Microorganism", title="Escherichia coli")
    >>> amx = api.create(bika_setup.antibiotics, "Antibiotic", title="Amoxicillin", abbreviation="AMX")
    >>> amp = api.create(bika_setup.antibiotics, "Antibiotic", title="Ampicillin", abbreviation="AMP")
    >>> amx.extrapolated_antibiotics = [api.get_uid(amp)]


Microorganism identification
............................

The microorganism identification analysis stores the identified
microorganisms in a multi-valued result:

    >>> sample = new_sample([get_service(IDENTIFICATION_KEY)])
    >>> analysis = sample.getAnalyses(full_objects=True)[0]
    >>> analysis.getResultType()
    'multiselect'

The result options are the active microorganisms, plus an explicit option for
when nothing was identified:

    >>> [option["ResultText"] for option in analysis.getResultOptions()]
    ['No culture growth obtained', 'Escherichia coli']

The analysis cannot be submitted when no microorganism is selected, so an
identification is never reported without a result:

    >>> analysis.setResult([])
    >>> analysis.getResult()
    '[]'

    >>> is_result_complete(analysis)
    False

    >>> isTransitionAllowed(analysis, "submit")
    False

    >>> transitioned = do_action_for(analysis, "submit")
    >>> api.get_workflow_status_of(analysis)
    'unassigned'

When no microorganism grew, the analyst has to choose the option explicitly:

    >>> no_growth = analysis.getResultOptions()[0]
    >>> analysis.setResult([str(no_growth["ResultValue"])])
    >>> is_result_complete(analysis)
    True

    >>> transitioned = do_action_for(analysis, "submit")
    >>> api.get_workflow_status_of(analysis)
    'to_be_verified'

And the same applies when a microorganism is identified:

    >>> sample = new_sample([get_service(IDENTIFICATION_KEY)])
    >>> analysis = sample.getAnalyses(full_objects=True)[0]
    >>> ecoli_option = analysis.getResultOptions()[1]
    >>> analysis.setResult([str(ecoli_option["ResultValue"])])
    >>> is_result_complete(analysis)
    True

    >>> transitioned = do_action_for(analysis, "submit")
    >>> api.get_workflow_status_of(analysis)
    'to_be_verified'


Extrapolated antibiotics
........................

Antibiotics are stored as result variables of AST analyses. Antibiotics that
are extrapolated from a representative one are added as additional, hidden
result variables:

    >>> sample = new_sample([gram])
    >>> ast_analyses = create_ast_analyses(sample, [RESISTANCE_KEY], ecoli, [amx])
    >>> sensitivity = ast_analyses[0]
    >>> [interim["keyword"] for interim in sensitivity.getInterimFields()]
    ['AMX', 'AMP']

    >>> get_interim(sensitivity, "AMP").get("hidden")
    True

    >>> api.get_uid(amx) == get_interim(sensitivity, "AMP").get("primary")
    True

Their value is not captured by the analyst, but inferred from the value of
the representative antibiotic when results are saved. Until then, the
analysis cannot be submitted:

    >>> set_interim_value(sensitivity, "AMX", "1")
    >>> get_interim(sensitivity, "AMP").get("value")
    ''

    >>> is_result_complete(sensitivity)
    False

    >>> isTransitionAllowed(sensitivity, "submit")
    False

The calculation assigns the category of the representative antibiotic to the
antibiotics extrapolated from it, and the analysis becomes submittable:

    >>> sensitivity.calculateResult(override=True)
    True

    >>> get_interim(sensitivity, "AMP").get("value")
    '1'

    >>> is_result_complete(sensitivity)
    True

    >>> transitioned = do_action_for(sensitivity, "submit")
    >>> api.get_workflow_status_of(sensitivity)
    'to_be_verified'


Selective reporting of extrapolated antibiotics
...............................................

The analysis for the selective reporting of extrapolated antibiotics stores
one multi-valued result variable per representative antibiotic, with the
antibiotics extrapolated from it as the available choices:

    >>> sample = new_sample([gram])
    >>> ast_analyses = create_ast_analyses(
    ...     sample, [REPORT_EXTRAPOLATED_KEY], ecoli, [amx])
    >>> report = ast_analyses[0]
    >>> get_interim(report, "AMX").get("result_type")
    'multichoice'

    >>> get_interim(report, "AMX").get("choices") == "{}:AMP".format(api.get_uid(amp))
    True

The selection is optional, so the result variable declares that empty values
are allowed:

    >>> get_interim(report, "AMX").get("allow_empty")
    True

Therefore the analysis can be submitted when no extrapolated antibiotic is
selected, either because no value was ever captured:

    >>> get_interim(report, "AMX").get("value")
    ''

    >>> is_result_complete(report)
    True

    >>> isTransitionAllowed(report, "submit")
    True

or because the selection was explicitly emptied, that is stored as an empty
list:

    >>> set_interim_value(report, "AMX", "[]")
    >>> is_result_complete(report)
    True

    >>> isTransitionAllowed(report, "submit")
    True

    >>> set_interim_value(report, "AMX", '[""]')
    >>> is_result_complete(report)
    True

    >>> isTransitionAllowed(report, "submit")
    True

And of course when an extrapolated antibiotic is selected:

    >>> set_interim_value(report, "AMX", '["{}"]'.format(api.get_uid(amp)))
    >>> is_result_complete(report)
    True

    >>> transitioned = do_action_for(report, "submit")
    >>> api.get_workflow_status_of(report)
    'to_be_verified'

Note that empty values are only allowed because the result variable says so.
Antibiotics from the other AST analyses do not, and still require a value:

    >>> sample = new_sample([gram])
    >>> ast_analyses = create_ast_analyses(sample, [RESISTANCE_KEY], ecoli, [amx])
    >>> sensitivity = ast_analyses[0]
    >>> get_interim(sensitivity, "AMX").get("allow_empty")

    >>> isTransitionAllowed(sensitivity, "submit")
    False
