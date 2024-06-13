Anitbiotic Sensitivity Testing
------------------------------

Running this test from the buildout directory:

    bin/test test_textual_doctests -t AST


Test Setup
..........

Needed Imports:

    >>> from DateTime import DateTime
    >>> from bika.lims import api
    >>> from bika.lims.utils.analysisrequest import create_analysisrequest
    >>> from plone.app.testing import TEST_USER_ID
    >>> from plone.app.testing import TEST_USER_PASSWORD
    >>> from plone.app.testing import setRoles

Variables:

    >>> portal = self.portal
    >>> request = self.request
    >>> setup = api.get_setup()
    >>> date_now = DateTime().strftime("%Y-%m-%d")

Functional Helpers:

    >>> def new_sample(services, client, contact, sampletype):
    ...     values = {
    ...         'Client': client.UID(),
    ...         'Contact': contact.UID(),
    ...         'DateSampled': date_now,
    ...         'SampleType': sampletype.UID()}
    ...     service_uids = map(api.get_uid, services)
    ...     sample = create_analysisrequest(client, request, values, service_uids)
    ...     return sample

We need to create some basic objects for the test:

    >>> setRoles(portal, TEST_USER_ID, ['LabManager',])
    >>> client = api.create(portal.clients, "Client", Name="Happy Hills", ClientID="HH", MemberDiscountApplies=True)
    >>> contact = api.create(client, "Contact", Firstname="Rita", Lastname="Mohale")
    >>> sampletype = api.create(setup.bika_sampletypes, "SampleType", title="Blood", Prefix="B")
    >>> labcontact = api.create(setup.bika_labcontacts, "LabContact", Firstname="Lab", Lastname="Manager")
    >>> department = api.create(portal.setup.departments, "Department", title="Microbiology", Manager=labcontact)
    >>> category = api.create(setup.bika_analysiscategories, "AnalysisCategory", title="Microbiology", Department=department)
    >>> g = api.create(setup.bika_analysisservices, "AnalysisService", title="GRAM Test", Keyword="G", Price="15", Category=category.UID(), Accredited=True)


Sample setup
............

Create a new sample:

    >>> sample = new_sample([g], client, contact, sampletype)
    >>> api.get_workflow_status_of(sample)
    'sample_due'
