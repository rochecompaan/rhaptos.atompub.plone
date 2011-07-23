#
# Test the Atom Pub browser view
#

import pdb;pdb.set_trace()
import unittest
import zope.interface

from Testing import ZopeTestCase
from Products.CMFPlone.tests import PloneTestCase

ZopeTestCase.installProduct('rhaptos.atompub.plone', quiet=1)

class TestAtomPub(PloneTestCase.PloneTestCase):

    def afterSetUp(self):
        import pdb;pdb.set_trace()
        self.addProfile('rhaptos.atompub.plone:default')

    def assertResults(self, result, expect):
        # Verifies ids of catalog results against expected ids
        lhs = [r.getId for r in result]
        lhs.sort()
        rhs = list(expect)
        rhs.sort()
        self.assertEqual(lhs, rhs)

    def test_publishAtomItem(self):
        return True


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestAtomPub))
    return suite
