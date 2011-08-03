from cStringIO import StringIO

from xml.dom.minidom import parse
from xml.parsers.expat import ExpatError

from Acquisition import aq_inner

from zope.interface import Interface, implements
from zope.publisher.interfaces.http import IHTTPRequest
from zope.component import adapts, getMultiAdapter, queryUtility

from webdav.NullResource import NullResource

from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from Products.CMFCore.interfaces import IFolderish
from Products.CMFCore.utils import getToolByName

from Products.CMFPlone.PloneTool import METADATA_DCNAME, METADATA_DC_AUTHORFIELDS

from Products.Archetypes.Marshall import formatRFC822Headers

from rhaptos.atompub.plone.interfaces import IAtomPubServiceAdapter

METADATA_MAPPING = {'dcterms:title': 'Title',
                    'dcterms:sub': 'Subject',
                    'dcterms:subject': 'Subject',
                    'dcterms:publisher': 'Publisher',
                    'dcterms:description': 'Description',
                    'dcterms:creators': 'Creators',
                    'dcterms:effective_date': 'effective_date',
                    'dcterms:expiration_date': 'expiration_date',
                    'dcterms:type': 'Type',
                    'dcterms:format': 'Format',
                    'dcterms:language': 'Language',
                    'dcterms:rights': 'Rights',
                    'dcterms:accessRights': 'accessRights',
                    'dcterms:rightsHolder': 'rightsHolder',
                    'dcterms:abstract': 'abstract',
                    'dcterms:alternative': 'alternative',
                    'dcterms:available': 'available',
                    'dcterms:bibliographicCitation': 'bibliographicCitation',
                    'dcterms:contributor': 'Contributors',
                    'dcterms:hasPart': 'hasPart',
                    'dcterms:hasVersion': 'hasVersion',
                    'dcterms:identifier': 'identifier',
                    'dcterms:isPartOf': 'isPartOf',
                    'dcterms:references': 'references',
                    'dcterms:source': 'source',
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
    
    # As specified by: http://bitworking.org/projects/atom/rfc5023.html#crwp
    # In answer to a successful POST one must return an:
    # Atom Entry Document
    atom_entry_document = ViewPageTemplateFile('atom_entry_document.pt')
    media_entry_representation = \
            ViewPageTemplateFile('media_entry_representation.pt')


    def __call__(self):
        # Adapt and call
        adapter = getMultiAdapter((aq_inner(self.context),
                                  self.request),
                                  IAtomPubServiceAdapter
                                 )
        obj = adapter()
        # TODO: some error messaging is in order here.
        # look at the rhaptos.swordservice.plone.sword.py decorator:
        # @show_error_document, maybe use that to decorate our __call__
        if not obj: return
        
        # set the Location header as required by rfc5023, section: 9.2 
        # 'Creating Resources with POST'
        response = self.request.response
        response.setHeader('Location', '%s/atompub/edit' % obj.absolute_url())
        response.setStatus(201)

        # return the correct result based on the content type
        content_type = self.request.getHeader('content-type').strip(';')
        if content_type == ATOMPUB_CONTENT_TYPE:
            result = self.atom_entry_document(entry=obj)
            return result
        else:
            result = self.media_entry_representation(entry=obj)
            return result

        return 'Nothing to do'


    def metadata(self, item):
        return item.getMetadataHeaders()


    def formatMetadata(self, data):
        # <dcterms:title>Title</dcterms:title>
        name = data[0].lower()
        content = data[1]
        return '<dcterms:%s>%s</dcterms:%s>' %(name, content, name)
    

class PloneFolderAtomPubAdapter(object):
    adapts(IFolderish, IHTTPRequest)

    def __init__(self, context, request):
        self.context = context
        self.request = request


    def __call__(self):
        context = self.context
        request = self.request
        response = request.response

        content_type = request.getHeader('content-type').strip(';')
        prefix = self._getPrefix(content_type)
        name = context.generateUniqueId(prefix)

        # fix the request headers to get the correct metadata mappings
        request = self._updateRequest(request, content_type)

        nullresouce = NullResource(context, name, request)
        nullresouce.__of__(context)
        nullresouce.PUT(request, response)

        # Look it up and finish up, then return it.
        obj = context._getOb(name)
        obj.PUT(request, response)
        obj.setTitle(request.get('Title', name))
        obj.reindexObject(idxs='Title')
        return obj

    
    def _updateRequest(self, request, content_type):
        """ The body.seek(0) looks funny, but I do that to make sure I get
            all the content, no matter who accessed the body file before me.
        """
        # then we update the body of the request
        if content_type == ATOMPUB_CONTENT_TYPE:
            body = request.get('BODYFILE')
            # update headers from the request body
            # make sure we read from the beginning
            body.seek(0)
            dom = parse(body)
            headers = self.getHeaders(dom, METADATA_MAPPING)

            content = self._getValueFromDOM('content', dom)
            title = self._getValueFromDOM('title', dom)
            request['Title'] = title

            header = formatRFC822Headers(headers)
            data = '%s\n\n%s' % (header, content.encode('utf-8'))
            length = len(data)
            request['Content-Length'] = length
            body_file = StringIO(data)
            request['BODYFILE'] = body_file
        return request
   

    def getHeaders(self, dom, mappings): 
        headers = []
        for name in mappings.keys():
            value = dom.getElementsByTagName(name)
            value = '\n'.join([str(v.firstChild.nodeValue) for v in value \
                               if v.firstChild is not None]
                             )
            headers.append((mappings[name], str(value)))
        return headers


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


