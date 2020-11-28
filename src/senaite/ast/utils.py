from bika.lims import api
from bika.lims import workflow as wf
from bika.lims.catalog import SETUP_CATALOG
from bika.lims.interfaces import ISubmitted
from bika.lims.interfaces import IVerified
from bika.lims.utils.analysis import create_analysis
from bika.lims.workflow import doActionFor
from senaite.ast import logger
from senaite.ast.config import AST_RESULTS_CHOICES
from senaite.ast.config import AST_SERVICE_KEYWORD

_marker = object()


def get_service(keyword, default=_marker):
    """Returns the Analysis Service for the given keyword, if any
    """
    query = {
        "portal_type": "AnalysisService",
        "getKeyword": keyword
    }
    brains = api.search(query, SETUP_CATALOG)
    if len(brains) == 1:
        return api.get_object(brains[0])
    elif default is _marker:
        raise KeyError("No service found for '{}'".format(keyword))
    return default


def new_analysis_id(sample, analysis_keyword):
    """Returns a new analysis id for an hypothetic new test with given keyword
    to prevent clashes with ids of other analyses from same sample
    """
    new_id = analysis_keyword
    analyses = sample.getAnalyses(getKeyword=analysis_keyword)
    if analyses:
        new_id = "{}-{}".format(analysis_keyword, len(analyses))
    return new_id


def create_ast_analysis(sample, microorganism, antibiotics):
    """Creates a new AST analysis
    """
    # Service to use as the template
    service = get_service(AST_SERVICE_KEYWORD)

    # Convert antibiotics to interims
    interims = map(to_interim, antibiotics)

    # Title of microorganism becomes the title of the analysis
    obj = api.get_object(microorganism)
    title = api.get_title(obj)

    # Create a new ID to prevent clashes
    new_id = new_analysis_id(sample, service.getKeyword())

    # Create the analysis
    analysis = create_analysis(sample, service, id=new_id)

    # Assign the name of the microorganism as the title
    analysis.setTitle(title)

    # Assign the antibiotics as interims
    analysis.setInterimFields(interims)

    # Initialize the analysis and reindex
    doActionFor(analysis, "initialize")
    analysis.reindexObject()

    return analysis


def update_ast_analysis(analysis, antibiotics):
    """Updates the ast analysis with the antibiotics passed-in
    """
    # There is nothing to do if the analysis has been verified
    analysis = api.get_object(analysis)
    if IVerified.providedBy(analysis):
        return

    # Convert the antibiotics to interims
    antibiotics = map(to_interim, antibiotics)

    # Compare the antibiotics passed-in with those assigned to the analysis
    keys = map(lambda i: i.get("keyword"), analysis.getInterimFields())
    abx = filter(lambda a: a["keyword"] not in keys, antibiotics)
    if not abx:
        # Analysis has all antibiotics assigned already
        return

    if ISubmitted.providedBy(analysis):
        # Analysis has been submitted already, retract
        succeed, message = wf.doActionFor(analysis, "retract")
        if not succeed:
            path = api.get_path(analysis)
            logger.error("Cannot retract analysis '{}'".format(path))
            return

    # Assign the antibiotics
    analysis.setInterimFields(antibiotics)
    analysis.reindexObject()


def to_interim(antibiotic):
    """Converts a list of antibiotics to a list of interims
    """
    if isinstance(antibiotic, dict):
        # Already an interim
        return antibiotic

    obj = api.get_object(antibiotic)
    return {
        "keyword": obj.abbreviation,
        "title": obj.abbreviation,
        "choices": AST_RESULTS_CHOICES,
        "value": "",
        "unit": "",
        "wide": False,
        "hidden": False,
    }
