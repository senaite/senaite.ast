# -*- coding: utf-8 -*-

from bika.lims import api
from datetime import datetime
from plone.app.layout.globals.interfaces import IViewView
from plone.memoize.view import memoize
from Products.CMFPlone.utils import safe_unicode
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from senaite.ast.config import MIC_KEY
from senaite.ast.config import RESISTANCE_KEY
from senaite.ast.config import ZONE_SIZE_KEY
from senaite.ast.utils import get_antibiotics
from senaite.ast.utils import get_ast_group
from senaite.ast.utils import get_interim_text
from senaite.core.api import dtime
from senaite.core.catalog import ANALYSIS_CATALOG
from senaite.core.decorators import readonly_transaction
from senaite.core.interfaces import IHideActionsMenu
from senaite.patient import api as patient_api
from six import StringIO
from zope.interface import implementer


@implementer(IHideActionsMenu, IViewView)
class WHONETExportView(BrowserView):
    """View for the export of AST results to a delimited text file format that
    can be imported into WHONET software (https://www.whonet.org) through
    the data import module BacLink
    """
    template = ViewPageTemplateFile("templates/export.pt")

    @readonly_transaction
    def __call__(self):

        # Form submit toggle
        form_submitted = self.form.get("submitted", False)

        # Buttons
        form_export = self.form.get("button_export", False)

        if form_submitted and form_export:
            # Search the analyses
            analyses = self.search_analyses()
            if analyses:

                # Generate the CSV-like data for Baclink
                output = self.get_export_output(analyses)

                # Establish the HTTP response header as text/csv file
                date = datetime.now().strftime("%Y%m%d%H%M")
                set_header = self.request.RESPONSE.setHeader
                set_header("Content-Type", "text/csv")
                set_header("Content-Length", len(output))
                set_header("Cache-Control", "no-store")
                set_header("Pragma", "no-cache")
                set_header("Content-Disposition",
                           "attachment;filename=\"export%s.csv\"" % date)
                output = safe_unicode(output).encode("utf-8")
                self.request.RESPONSE.write(output)
                return

        return self.template()

    @property
    def form(self):
        """Returns the form object associated to the current request
        """
        return self.request.form or {}

    @property
    def created_from(self):
        """Returns the creation date of the oldest AST analysis to export
        """
        # Default to first day of current month
        default = datetime.now()
        default = datetime(default.year, default.month, 1)
        date_from = self.form.get("created_from", None)
        date_from = api.to_date(date_from, default=default)
        return date_from.strftime("%Y-%m-%d")

    @property
    def created_to(self):
        """Returns the creation date of the earlier AST analysis to export
        """
        date_to = self.form.get("created_to", None)
        date_to = api.to_date(date_to, default=datetime.now())
        return date_to.strftime("%Y-%m-%d")

    def search_analyses(self):
        """Returns a list of zone size and MIC analyses that match with the
        date criteria, from published samples only
        """
        query = {
            "portal_type": "Analysis",
            "review_state": ["verified", "published"],
            "getKeyword": [ZONE_SIZE_KEY, MIC_KEY],
            "date_sampled": {
                "query": [self.created_from, self.created_to],
                "range": "min:max"},
            "sort_on": "getRequestID",
            "sort_order": "ascending"
        }

        brains = api.search(query, ANALYSIS_CATALOG)

        # Fill with analysis objects
        analyses = map(self.get_object, brains)
        analyses = filter(None, analyses)

        # Exclude analyses that belong to not-yet-published samples
        analyses = filter(self.is_sample_published, analyses)

        return list(analyses)

    def get_object(self, brain_object_uid, default=None):
        """Returns the object or default if not reachable
        """
        try:
            return api.get_object(brain_object_uid, default=default)
        except AttributeError:
            return default

    def is_sample_published(self, analysis):
        """Returns whether the sample of the analysis has been published
        """
        sample = analysis.getRequest()
        return api.get_review_status(sample) == "published"

    def get_export_output(self, analyses, delimiter=","):
        """Returns a CSV-like string with the data to be exported
        """
        # Get all antibiotics and sort them by title
        antibiotics = get_antibiotics(analyses)

        # Write the file header
        output = StringIO()
        header = [
            "Hospital",
            "Medical record number",
            "Patient first name",
            "Patient last name",
            "Birthdate",
            "Age",
            "Sex",
            "Ward",
            "Accession number",
            "Sample type",
            "Collection date",
            "Date of admission",
            "Relevant clinical information",
            "Current antibiotics",
            "Microorganism",
            "Method",
        ]

        # Add paired columns per antibiotic: measurement + interpretation
        for antibiotic in antibiotics:
            title = api.get_title(antibiotic)
            header.append(title)
            header.append("{}_INTERP".format(title))

        def wrap_quotes(value):
            if not value:
                value = ""
            val = str(value).replace('"', '\'')
            return '"{}"'.format(val)

        # Wrap values in double-quotes
        header = map(wrap_quotes, header)
        output.write(delimiter.join(header)+"\r\n")

        # Iterate over analyses and build the data lines
        for analysis in analyses:

            # Initialize the data line
            data_line = []

            # Extend the data line with the sample info
            sample = analysis.getRequest()
            sample_info = self.get_sample_info(sample)
            data_line.extend([
                sample_info["client"],
                sample_info["mrn"],
                sample_info["patient_firstname"],
                sample_info["patient_lastname"],
                sample_info["dob"],
                sample_info["age"],
                sample_info["sex"],
                sample_info["ward"],
                sample_info["id"],
                sample_info["sample_type"],
                sample_info["date_sampled"],
                sample_info["date_received"],
                sample_info["clinical_info"],
                sample_info["antibiotics"],
            ])

            # Microorganism name (is the ShortTitle)
            data_line.append(analysis.getShortTitle())
            data_line.append(self.get_method(analysis))

            # Get the resistance sibling for S/I/R interpretation
            ast_group = get_ast_group(analysis)
            resistance = ast_group.get(RESISTANCE_KEY)

            # Extend with paired measurement + interpretation
            for antibiotic in antibiotics:
                data_line.append(self.get_result_for(analysis, antibiotic))
                data_line.append(self.get_interp_for(resistance, antibiotic))

            # Wrap values in double-quotes
            data_line = map(wrap_quotes, data_line)
            output.write(delimiter.join(data_line)+"\r\n")

        output.seek(0)

        # Get the raw data and close the stream
        data = output.getvalue()
        output.close()

        return data

    def get_result_for(self, analysis, antibiotic):
        """Extracts the result for the analysis and antibiotic passed in, if
        any. Returns empty string otherwise
        """
        antibiotic_uid = api.get_uid(antibiotic)
        for result in analysis.getInterimFields():
            if result.get("uid") == antibiotic_uid:
                return result.get("value", "")

        return ""

    def get_interp_for(self, analysis, antibiotic):
        """Extracts the S/I/R interpretation for the analysis and antibiotic
        passed in. Returns empty string if not available
        """
        if not analysis:
            return ""
        antibiotic_uid = api.get_uid(antibiotic)
        for interim in analysis.getInterimFields():
            if interim.get("uid") == antibiotic_uid:
                return get_interim_text(interim, default="")
        return ""

    def get_method(self, analysis):
        """Returns the test method name for BacLink based on the analysis
        keyword: 'Disk' for disk diffusion, 'MIC' for MIC
        """
        keyword = analysis.getKeyword()
        if keyword == ZONE_SIZE_KEY:
            return "Disk"
        if keyword == MIC_KEY:
            return "MIC"
        return ""

    def get_age_ymd(self, dob, date_sampled):
        return patient_api.get_age_ymd(dob, date_sampled) or ""

    def get_ward(self, sample):
        accessor = getattr(sample, "getWard", None)
        if callable(accessor):
            return accessor()
        return None

    def get_sample_info(self, sample):
        """Returns a dictionary that represents the sample object passed-in
        """
        mrn = sample.getMedicalRecordNumberValue()
        dob = sample.getDateOfBirth()[0]

        client = sample.getClient()
        sample_type = sample.getRawSampleType()
        date_sampled = sample.getDateSampled()
        date_received = sample.getDateReceived()
        # XXX Port ClinicalInformation functionality
        field = sample.getField("AdditionalNotes")
        clinical_info = field.get(sample) if field else None
        clinical_info = clinical_info or ""
        # XXX Port CurrentAntibiotics functionality
        field = sample.getField("CurrentAntibiotics")
        antibiotics = field.get(sample) if field else None
        antibiotics = antibiotics or []
        antibiotics = ", ".join(map(api.get_title, antibiotics))

        patient_field = sample.getField("PatientFullName")
        firstname = patient_field.get_firstname(sample)
        lastname = patient_field.get_lastname(sample)

        ward = self.get_ward(sample)
        ward = api.get_title(ward) if ward else ""

        return {
            "client": api.get_title(client),
            "mrn": mrn,
            "patient_firstname": firstname,
            "patient_lastname": lastname,
            "dob": self.format_date(dob),
            "age": self.get_age_ymd(dob, date_sampled),
            "sex": sample.getSex(),
            "ward": ward,
            "id": api.get_id(sample),
            "sample_type": self.get_title(sample_type),
            "date_sampled": self.format_date(date_sampled),
            "date_received": self.format_date(date_received),
            "clinical_info": clinical_info,
            "antibiotics": antibiotics,
        }

    @memoize
    def get_title(self, uid, default=""):
        """Returns the title of the object with the uid passed in
        """
        obj = api.get_object_by_uid(uid, default=None)
        if not obj:
            return default
        return api.get_title(obj)

    def format_date(self, date_obj, default=""):
        if not dtime.is_date(date_obj):
            return default
        return dtime.to_localized_time(date_obj, long_format=False,
                                       context=self.context, default=default)
