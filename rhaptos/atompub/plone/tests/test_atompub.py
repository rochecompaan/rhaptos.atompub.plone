#
# Test the Atom Pub browser view
#

import sys
import os
import DateTime

from urllib2 import HTTPError
from cStringIO import StringIO

import unittest
import zope.interface
from ZPublisher.HTTPRequest import HTTPRequest
from ZPublisher.HTTPResponse import HTTPResponse

from xml.dom.minidom import parseString
from xml.parsers.expat import ExpatError

from Testing import ZopeTestCase
from Products.CMFPlone.tests import PloneTestCase

from rhaptos.atompub.plone.browser.atompub import AtomPubService

# TODO
# replace ../../ with os.cwd
# move files into data subdir

current_dir = os.path.dirname(__file__)
PATH_PREFIX = os.path.join(current_dir, 'data')
BAD_FILE = os.path.join(PATH_PREFIX, 'bad_atom.xml')
GOOD_FILE = os.path.join(PATH_PREFIX, 'good_atom.xml')
EXPECTED_RESULT = os.path.join(PATH_PREFIX, 'atom_post_expected_result.xml')

GIF_FILE = {'filename': 'beach.gif',
            'extension': 'gif',
            'content_type': 'image/gif', }


ZopeTestCase.installProduct('rhaptos.atompub.plone', quiet=1)
PloneTestCase.setupPloneSite()

class TestAtomPub(PloneTestCase.FunctionalTestCase):

    def afterSetUp(self):
        self.addProfile('rhaptos.atompub.plone:default')
        super(TestAtomPub, self).afterSetUp()

    
    def testAtomFeedView(self):
        """
        Add a folder and a file.
        Get the atom feed.
        """
        creation_date = DateTime.DateTime()
        contents = 'A test file'

        id = self.folder.invokeFactory('Folder', 'workspace')
        folder = self.folder._getOb(id)
        id = folder.invokeFactory('File', 'test_file')
        file = folder._getOb(id)
        file.creation_date = creation_date
        file.setFile(contents)

        view = folder.restrictedTraverse('@@atom')
        atom = view()
        dom = parseString(atom)


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

        content_type= 'application/atom+xml'
        view = self._getAtomPubBrowserView(bad_xml, content_type)
        self.failUnlessRaises(ExpatError, view)


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
        
        content_type = 'application/atom+xml'
        #good_xml = self._getGoodXMLPayload(GOOD_FILE, now)
        xml_file = open(GOOD_FILE, 'rb')
        good_xml = xml_file.read()
        xml_file.close()
        view = self._getAtomPubBrowserView(good_xml, content_type)
        result = view()

        result_dom = parseString(result)
        self._compareResultToExpectedValues(result_dom, expected_dom)


    def _test_uploadImage(self, details_dict):
        filename = details_dict['filename']
        path = os.path.join(PATH_PREFIX, filename)
        image_file = open(path, 'rb')
        image_content = image_file.read()
        image_file.close()
        
        #disposition = 'attachment;filename=%s' %filename
        context = self.folder
        content_type = details_dict['content_type']
        view = self._getAtomPubBrowserView(image_content, content_type)
        results = view()


    def test_UploadGif(self):
        self._test_uploadImage(GIF_FILE)


    def _getAtomPubBrowserView(self, payload, content_type):
        req = self._getFauxRequest(payload, content_type)
        req.processInputs()
        context = self.folder
        view = AtomPubService(context, req)
        return view

    
    def _getFauxRequest(self, payload, content_type):
        # environ['method'] = 'POST'
        # environ['content-disposition'] = disposition
        # environ['CONTENT_DISPOSITION'] 
        # environ['slug'] = 'The Beach'
        # environ['charset']= 'utf-8'
        # environ['BODY'] = payload

        resp = HTTPResponse(stdout=sys.stdout)

        environ = {}
        environ['SERVER_NAME']='foo'
        environ['SERVER_PORT']='80'
        environ['REQUEST_METHOD'] = 'POST'
        environ['METHOD'] = 'POST'
        environ['CONTENT_TYPE'] = content_type
        environ['CONTENT_LENGTH'] = len(payload)

        file = StringIO(payload)
        req = HTTPRequest(stdin=file, environ=environ, response=resp)
        return req


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

        #self.assertEqual(self.getPageId(result_dom),
        #                 self.getPageId(expected_dom))

        #self.assertEqual(self.getUpdatedDate(result_dom),
        #                 self.getUpdatedDate(expected_dom))

        self.assertEqual(self.getAuthor(result_dom),
                         self.getAuthor(expected_dom))

        self.assertEqual(self.getContent(result_dom),
                         self.getContent(expected_dom))

        self.assertEqual(self._getValueFromDOM('title', result_dom),
                         self._getValueFromDOM('title', expected_dom))

        self.assertEqual(self._getValueFromDOM('subject', result_dom),
                         self._getValueFromDOM('subject', expected_dom))

        self.assertEqual(self._getValueFromDOM('publisher', result_dom),
                         self._getValueFromDOM('publisher', expected_dom))

        self.assertEqual(self._getValueFromDOM('description', result_dom),
                         self._getValueFromDOM('description', expected_dom))

        self.assertEqual(self._getValueFromDOM('creators', result_dom),
                         self._getValueFromDOM('creators', expected_dom))

        self.assertEqual(self._getValueFromDOM('effective_date', result_dom),
                         self._getValueFromDOM('effective_date', expected_dom))

        self.assertEqual(self._getValueFromDOM('expiration_date', result_dom),
                         self._getValueFromDOM('expiration_date', expected_dom))

        self.assertEqual(self._getValueFromDOM('type', result_dom),
                         self._getValueFromDOM('type', expected_dom))

        self.assertEqual(self._getValueFromDOM('format', result_dom),
                         self._getValueFromDOM('format', expected_dom))

        self.assertEqual(self._getValueFromDOM('language', result_dom),
                         self._getValueFromDOM('language', expected_dom))

        self.assertEqual(self._getValueFromDOM('rights', result_dom),
                         self._getValueFromDOM('rights', expected_dom))


    def _getValueFromDOM(self, name, dom):
        value = None
        elements = dom.getElementsByTagName(name)
        if elements:
            child = elements[0].firstChild
            value = child and child.nodeValue or None
        return value


    def getPageTitle(self, element):
        return self._getValueFromDOM('title', element)

    
    def getPageId(self, element):
        return self._getValueFromDOM('id', element)


    def getUpdatedDate(self, element):
        return self._getValueFromDOM('update', element)


    def getAuthor(self, element):
        return self._getValueFromDOM('author', element)


    def getContent(self, element):
        return self._getValueFromDOM('content', element)


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
