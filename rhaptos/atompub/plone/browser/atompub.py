from xml.dom.minidom import parseString
from xml.parsers.expat import ExpatError

from Acquisition import aq_base
from zope.interface import Interface, implements

from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from Products.CMFCore.utils import getToolByName

METADATA_MAPPING = {'slug': 'title',
                    'name': 'creator',
                   }

ATOMPUB_CONTENT_TYPE = 'application/atom+xml'


class IAtomPubService(Interface):
    """ Marker interface for AtomPuv service """

class AtomPubService(BrowserView):
    """ Accept a POST, use the content type registry to figure out what type
        to create.
        Mangle the headers and body to fit the type created.
        Call the PUT method to finalise the object creation.
        Return a representation of the object based on the type that was
        created.
    """
    implements(IAtomPubService)

    _atompub_result = ViewPageTemplateFile('atompub_result.pt')
    _atompub_media_result = ViewPageTemplateFile('atompub_media_result.pt')


    def __call__(self):
        context = self.context
        request = self.request
        response = request.response

        content_type = request.getHeader('content-type').strip(';')
        prefix = self._getPrefix(content_type)
        name = context.generateUniqueId(prefix)

        body = request.get('body', request.get('BODY', None))

        obj = self._createObject(context, request, name, content_type, body)
        if not obj: return None
        
        # fix the request headers to get the correct metadata mappings
        request = self._updateRequest(request, content_type, body)

        # finalise the creation by using the PUT method
        obj.__of__(context)
        obj.PUT(request, response)

        # return the correct result based on the content type
        if content_type == ATOMPUB_CONTENT_TYPE:
            result = self._atompub_result(entry=obj)
            return result
        else:
            result = _atompub_media_result(entry=obj)
            return result

        return 'Nothing to do'

    
    def _createObject(self, context, request, name, content_type, body):
        """ This code was adapted from:
            Products.CMFCore.PortaFolder.PUT_factory
        """
        registry = getToolByName(context, 'content_type_registry', None)
        if registry is None:
            return None

        typeObjectName = registry.findTypeName(name, content_type, body)
        if typeObjectName is None:
            return None

        context.invokeFactory(typeObjectName, name)

        # invokeFactory does too much, so the object has to be removed again
        obj = aq_base(context._getOb(name))
        context._delObject(name)
        return obj


    def _updateRequest(self, request, content_type, body):
        # first we update the headers
        request = self._changeHeaderNames(request, METADATA_MAPPING)

        # then we update the body of the request
        if content_type == ATOMPUB_CONTENT_TYPE:
            # update headers from the request body
            dom = parseString(body)
            request = self._addHeadersFromDOM(request, dom, METADATA_MAPPING)
            body = self._getValueFromDOM('content', dom)
        request['BODY'] = body

        return request
   

    def _changeHeaderNames(self, request, mappings):
        for old_key, new_key in mappings.items():
            value = request.get(old_key, None)
            if value:
                request.set(new_key, value)
        return request


    def _addHeadersFromDOM(self, request, dom, mappings):
        for key in mappings.keys():
            value = self._getValueFromDOM(key, dom)
            if value is not None:
                request.set(key, value)
        return request


    def _getValueFromDOM(self, name, dom):
        value = None
        elements = dom.getElementsByTagName(name)
        if elements:
            value = elements[0].firstChild.nodeValue
        return value


    def _getHtmlBodyFromDOM(self, dom):
        return self._getValueFromDOM('content', dom)

    
    def _getPrefix(self, seed):
        tmp_name = seed.replace('/', '_')
        tmp_name = tmp_name.replace('+', '_')
        tmp_name = tmp_name.strip(';')
        return tmp_name

