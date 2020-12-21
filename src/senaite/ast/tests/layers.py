import transaction
from plone.app.testing import applyProfile
from plone.app.testing import FunctionalTesting
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import PloneSandboxLayer
from plone.testing import zope


class BaseLayer(PloneSandboxLayer):
    defaultBases = (PLONE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        super(BaseLayer, self).setUpZope(app, configurationContext)

        # Load ZCML
        import bika.lims
        import senaite.app.listing
        import senaite.microorganism

        self.loadZCML(package=bika.lims)
        self.loadZCML(package=senaite.core)
        self.loadZCML(package=senaite.app.listing)
        self.loadZCML(package=senaite.app.spotlight)
        self.loadZCML(package=senaite.impress)
        self.loadZCML(package=senaite.lims)
        self.loadZCML(package=senaite.abx)
        self.loadZCML(package=senaite.microorganism)
        self.loadZCML(pakcage=senaite.ast)

        # Install product and call its initialize() function
        zope.installProduct(app, "Products.TextIndexNG3")
        zope.installProduct(app, "bika.lims")
        zope.installProduct(app, "senaite.core")
        zope.installProduct(app, "senaite.app.listing")
        zope.installProduct(app, "senaite.app.spotlight")
        zope.installProduct(app, "senaite.impress")
        zope.installProduct(app, "senaite.lims")
        zope.installProduct(app, "senaite.abx")
        zope.installProduct(app, "senaite.microorganism")
        zope.installProduct(app, "senaite.ast")

    def setUpPloneSite(self, portal):
        # Install into Plone site using portal_setup
        applyProfile(portal, "senaite.core:default")
        applyProfile(portal, "senaite.databox:default")
        transaction.commit()


BASE_LAYER_FIXTURE = BaseLayer()
BASE_TESTING = FunctionalTesting(
    bases=(BASE_LAYER_FIXTURE,), name="SENAITE.AST:BaseTesting")
