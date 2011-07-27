import zipfile
from urllib2 import HTTPError
from xml.dom.minidom import parseString
from xml.parsers.expat import ExpatError
import lxml

from zope.interface import Interface, implements

from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from Products.CMFCore.utils import getToolByName


class IAtomPubService(Interface):
    """ Marker interface for AtomPuv service """

class AtomPubService(BrowserView):
    """
    HTTPErrors
      HTTPClientError
        * 400 - HTTPBadRequest
        * 401 - HTTPUnauthorized
        * 402 - HTTPPaymentRequired
        * 403 - HTTPForbidden
        * 404 - HTTPNotFound
        * 405 - HTTPMethodNotAllowed
        * 406 - HTTPNotAcceptable
        * 407 - HTTPProxyAuthenticationRequired
        * 408 - HTTPRequestTimeout
        * 409 - HTTPConfict
        * 410 - HTTPGone
        * 411 - HTTPLengthRequired
        * 412 - HTTPPreconditionFailed
        * 413 - HTTPRequestEntityTooLarge
        * 414 - HTTPRequestURITooLong
        * 415 - HTTPUnsupportedMediaType
        * 416 - HTTPRequestRangeNotSatisfiable
        * 417 - HTTPExpectationFailed
      HTTPServerError
        * 500 - HTTPInternalServerError
        * 501 - HTTPNotImplemented
        * 502 - HTTPBadGateway
        * 503 - HTTPServiceUnavailable
        * 504 - HTTPGatewayTimeout
        * 505 - HTTPVersionNotSupported
    """
    implements(IAtomPubService)

    STATUS_OK = 201
    STATUS_BADREQUEST = 400
    STATUS_INTERNALSERVER_ERROR = 500
    STATUS_NOTIMPLEMENTED = 501
    _messages = {STATUS_OK: 'Created',
                 STATUS_BADREQUEST: 'Submit a valid form.',
                 STATUS_INTERNALSERVER_ERROR: 'Invalid XML',
                 STATUS_NOTIMPLEMENTED: 'Not implemented',
                }

    _atompub_submit_form = ViewPageTemplateFile('atompub_submit.pt')
    _atompub_result = ViewPageTemplateFile('atompub_result.pt')

    def __call__(self):
        content_type = self.getContentType(self.request)
        if content_type == 'application/atom+xml;':
            return self.processAtomPubBody(self.request)
        if content_type == 'application/octetstream;':
            # Would be better as a 501 - HTTPNotImplemented
            error_code = self.STATUS_NOTIMPLEMENTED
            self.raiseException(request, HTTPError, error_code)
        
        # Clearly we did not understand the request.
        # We should probably raise a:
        # 400 - HTTPBadRequest
        # or
        # 501 - HTTPNotImplemented
        error_code = self.STATUS_NOTIMPLEMENTED
        self.raiseException(request, HTTPError, error_code)
        return 'Nothing to do'
    

    def processAtomPubBody(self, request):
        """
        Grab the body from the request, parse it. Then walk the tree
        and create the objects as required.
        """
        # we start off believing all is well
        status = self.STATUS_OK

        # get the xml
        content = self.getBody(self.request)

        # get the DOM from the xml
        try:
            root = parseString(content)
        except ExpatError, e:
            error_code = self.STATUS_INTERNALSERVER_ERROR
            self.raiseException(request, HTTPError, error_code)

        # get the relevant elements from the DOM
        page_title = self.getPageTitle(root)
        page_content = self.getPageContent(root)
        page_update_date = self.getPageUpdatedDate(root)
        page_metadata = self.getPageMetaData(root)

        # create the necessary objects
        new_id = self.context.invokeFactory('Document',
                                            id = page_title,
                                            title = page_title,
                                            text = page_content,
                                           )
        entry = self.context._getOb(new_id)
        entry.setModificationDate(page_update_date)
        
        # setup the response
        response = self.request.response
        result = self._atompub_result(entry=entry)
        location = '%s/edit' %entry.absolute_url()

        response.setHeader('status', '%s %s' %(status, self._messages[status]))
        response.setHeader('Content-Length', len(result))
        response.setHeader('Content-Type', 'application/atom+xml;type=entry;charset="utf-8"')
        response.setHeader('Location', location)

        return result
    

    def getPageTitle(self, element):
        elements = element.getElementsByTagName('title')
        if not elements:
            return ''
        title = elements[0].firstChild.nodeValue
        return title

    
    def getPageId(self):
        return self.context.generateUniqueId('atompub')


    def getPageContent(self, element):
        elements = element.getElementsByTagName('content')
        if not elements:
            return ''
        content = elements[0].firstChild.nodeValue
        return content
    

    def getPageUpdatedDate(self, element):
        elements = element.getElementsByTagName('updated')
        if not elements:
            return ''
        updated = elements[0].firstChild.nodeValue
        return updated


    def getPageMetaData(self, element):
        return {'Title': self.getPageTitle(element)}


    def getContentType(self, request):
        """
        TODO:
        Figure out why my Content_Type is going missing in the during testing.
        """
        content_type = request.get('Content-Type',
                                   request.get('content-type', None))
        if not content_type:
            # this is the preferred call that will check a whole lot more
            # options than my little call above. In a perfect world the
            # two will return the same thing.
            content_type = request.getHeader('Content-Type')
        return content_type


    def getBody(self, request):
        body = request.get('body', request.get('BODY', None))
        return body


    def raiseException(self, request, error_type, error_code):
        full_url = self.request['ACTUAL_URL']
        response = self.request.response
        headers = response.headers
        raise error_type(full_url,
                         error_code,
                         self._messages[error_code],
                         headers,
                         None
                        )


    def atompub_submit_form(self):
        return self._atompub_submit_form()
