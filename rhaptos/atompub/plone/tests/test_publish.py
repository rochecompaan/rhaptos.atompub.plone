#
# Test the Atom Pub browser view
#

from cStringIO import StringIO
import unittest
import zope.interface
from urllib2 import HTTPError
import DateTime
from xml.dom.minidom import parseString

from Testing import ZopeTestCase
from Products.CMFPlone.tests import PloneTestCase

from rhaptos.atompub.plone.browser.views import AtomPubService

BAD_FILE = '../../src/rhaptos.atompub.plone/rhaptos/atompub/plone/tests/bad_atom.xml'
GOOD_FILE = '../../src/rhaptos.atompub.plone/rhaptos/atompub/plone/tests/good_atom.xml'
EXPECTED_RESULT = '../../src/rhaptos.atompub.plone/rhaptos/atompub/plone/tests/atom_post_expected_result.xml'
GIF_FILE = '../../src/rhaptos.atompub.plone/rhaptos/atompub/plone/tests/beach.gif'
JPEG_FILE = '../../src/rhaptos.atompub.plone/rhaptos/atompub/plone/tests/beach.jpeg'
PJPEG_FILE = '../../src/rhaptos.atompub.plone/rhaptos/atompub/plone/tests/beach.pjpeg'
PNG_FILE = '../../src/rhaptos.atompub.plone/rhaptos/atompub/plone/tests/beach.png'
SVG_FILE = '../../src/rhaptos.atompub.plone/rhaptos/atompub/plone/tests/beach.svg'
TIFF_FILE = '../../src/rhaptos.atompub.plone/rhaptos/atompub/plone/tests/beach.tiff'
ICO_FILE = '../../src/rhaptos.atompub.plone/rhaptos/atompub/plone/tests/beach.ico'


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
    
    
    def test_publishBadAtomXML(self):
        """
         See what happens when we throw bad xml at the view.
        """
        xml_file = open(BAD_FILE, 'rb')
        bad_xml = xml_file.read()
        xml_file.close()

        view = self._getAtomPubBrowserView(bad_xml)
        self.failUnlessRaises(HTTPError, view)


    def test_publishGoodAtomXML(self):
        """
         See what happens when we try proper xml on the view.
        """
        now = DateTime.DateTime()

        # expected results DOM including the update date
        efile = open(EXPECTED_RESULT, 'rb')
        expected_dom = parseString(efile.read())
        efile.close()
        expected_dom = self.setUpdateDate(expected_dom, now)
        
        good_xml = self._getGoodXMLPayload(GOOD_FILE, now)
        view = self._getAtomPubBrowserView(good_xml)
        result = view()

        result_dom = parseString(result)
        self._compareResultToExpectedValues(result_dom, expected_dom)


    def _test_UploadImage(self, filename, imagetype):
        context = self.folder
        request = self.portal.REQUEST
        
        image_file = open(filename, 'rb')
        image_content = image_file.read()
        image_file.close()

        request['method'] = 'POST'
        request['Content-Type'] = imagetype 
        request['Content-Length'] = len(image_content)
        request['Slug'] = 'The Beach'
        request['BODY'] = image_content

        view = AtomPubService(context, request)
        results = view()


    def test_UploadGif(self):
        self._test_UploadImage(GIF_FILE, 'image/gif')


    def test_UploadJpeg(self):
        self._test_UploadImage(JPEG_FILE, 'image/jpeg')


    def test_UploadPjpeg(self):
        self._test_UploadImage(JPEG_FILE, 'image/pjpeg')


    def test_UploadPng(self):
        self._test_UploadImage(PNG_FILE, 'image/png')


    def test_UploadSvg(self):
        self._test_UploadImage(SVG_FILE, 'image/svg+xml')


    def test_UploadTiff(self):
        self._test_UploadImage(TIFF_FILE, 'image/tiff')


    def test_UploadIco(self):
        self._test_UploadImage(ICO_FILE, 'image/vnd.microsoft.icon')


    def _getAtomPubBrowserView(self, xml_payload):
        context = self.folder
        request = self.portal.REQUEST

        #request['content-disposition']
        request['method'] = 'POST'
        request['Content-Type'] = 'application/atom+xml;'
        request['charset']= 'utf-8'
        request['Content-Length'] = len(xml_payload)
        request['BODY'] = xml_payload

        view = AtomPubService(context, request)
        return view


    def _getGoodXMLPayload(self, filename, now):
        xml_file = open(filename, 'rb')
        payload_dom = parseString(xml_file.read())
        xml_file.close()

        self.setUpdateDate(payload_dom, now)
        xml_payload = payload_dom.toxml()
        return xml_payload

    
    def _compareResultToExpectedValues(self,result_dom, expected_dom):
        self.assertEqual(self.getPageTitle(result_dom),
                         self.getPageTitle(expected_dom))

        self.assertEqual(self.getPageId(result_dom),
                         self.getPageId(expected_dom))

        #self.assertEqual(self.getUpdatedDate(result_dom),
        #                 self.getUpdatedDate(expected_dom))

        self.assertEqual(self.getAuthor(result_dom),
                         self.getAuthor(expected_dom))

        self.assertEqual(self.getContent(result_dom),
                         self.getContent(expected_dom))



    def getPageTitle(self, element):
        elements = element.getElementsByTagName('title')
        if not elements:
            return ''
        title = elements[0].firstChild.nodeValue
        return title

    
    def getPageId(self, element):
        elements = element.getElementsByTagName('id')
        if not elements:
            return ''
        id = elements[0].firstChild.nodeValue
        return id


    def getUpdatedDate(self, element):
        elements = element.getElementsByTagName('updated')
        if not elements:
            return ''
        updated = elements[0].firstChild.nodeValue
        return updated


    def getAuthor(self, element):
        elements = element.getElementsByTagName('author')
        if not elements:
            return ''
        author = elements[0].firstChild.nodeValue
        return author


    def getContent(self, element):
        elements = element.getElementsByTagName('content')
        if not elements:
            return ''
        content = elements[0].firstChild.nodeValue
        return content


    def setUpdateDate(self, dom, now):
        # 2011/07/27 13:54:27 GMT+2
        #dt = DateTime.DateTime.strftime(now, '%Y/%m/%d %H:%M:%s')
        elements = dom.getElementsByTagName('updated')
        elements[0].firstChild.nodeValue = now
        return dom


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestAtomPub))
    return suite
