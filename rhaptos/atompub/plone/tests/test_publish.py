#
# Test the Atom Pub browser view
#

from cStringIO import StringIO
import unittest
import zope.interface
from urllib2 import HTTPError

from Testing import ZopeTestCase
from Products.CMFPlone.tests import PloneTestCase

from rhaptos.atompub.plone.browser.views import AtomPubService

BAD_FILE = '../../src/rhaptos.atompub.plone/rhaptos/atompub/plone/tests/bad_atom.xml'
GOOD_FILE = '../../src/rhaptos.atompub.plone/rhaptos/atompub/plone/tests/good_atom.xml'


ZopeTestCase.installProduct('rhaptos.atompub.plone', quiet=1)

class TestAtomPub(PloneTestCase.FunctionalTestCase):

    def afterSetUp(self):
        super(TestAtomPub, self).afterSetUp()


    def test_existsPublishAtomBrowserView(self):
        """
        Let's just see if it is here.
        """
        request = self.portal.REQUEST
        browser = self.getBrowser(loggedIn=True)
        self.portal.restrictedTraverse(
            ''.join(self.portal.getPhysicalPath())+'/@@atompub')
    
    
    def _getAtomPubBrowserView(self, file_name):
        context = self.folder
        request = self.portal.REQUEST

        xml_file = open(file_name, 'rb')
        xml_payload = xml_file.read()
        xml_file.close()

        #request['content-disposition']
        request['method'] = 'POST'
        request['Content-Type'] = 'application/atom+xml;'
        request['charset']= 'utf-8'
        request['Content-Length'] = len(xml_payload)
        request['BODY'] = xml_payload

        view = AtomPubService(context, request)
        return view


    def test_publishBadAtomXML(self):
        """
         See what happens when we throw bad xml at the view.
        """
        view = self._getAtomPubBrowserView(BAD_FILE)
        self.failUnlessRaises(HTTPError, view)


    def test_publishGoodAtomXML(self):
        """
         See what happens when we try proper xml on the view.
        """
        import pdb;pdb.set_trace()
        view = self._getAtomPubBrowserView(GOOD_FILE)
        result = view()


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestAtomPub))
    return suite
