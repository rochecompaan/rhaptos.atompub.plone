from copy import copy
from cStringIO import StringIO

from ZServer import LARGE_FILE_THRESHOLD
from xml.dom.minidom import parse
from xml.parsers.expat import ExpatError

from Acquisition import aq_inner, aq_base

from zope.interface import Interface, implements
from zope.publisher.interfaces.http import IHTTPRequest
from zope.component import adapts, getMultiAdapter, queryUtility

from webdav.NullResource import NullResource

from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from Products.CMFCore.interfaces import IFolderish
from Products.CMFCore.utils import getToolByName

from Products.Archetypes.Marshall import formatRFC822Headers

from rhaptos.atompub.plone.interfaces import IAtomPubServiceAdapter


METADATA_MAPPING =\
        {'title': 'title',
         'updated': 'modified',
         'author': 'creator',
         'sub': 'subject',
         'subject': 'subject',
         'publisher': 'publisher',
         'description': 'description',
         'creators': 'creators',
         'effective_date': 'effective_date',
         'expiration_date': 'expiration_date',
         'type': 'Type',
         'format': 'format',
         'language': 'language',
         'rights': 'rights',
         'accessRights': 'accessRights',
         'rightsHolder': 'rightsHolder',
         'abstract': 'abstract',
         'alternative': 'alternative',
         'available': 'available',
         'bibliographicCitation': 'bibliographicCitation',
         'contributor': 'contributors',
         'hasPart': 'hasPart',
         'hasVersion': 'hasVersion',
         'identifier': 'identifier',
         'isPartOf': 'isPartOf',
         'references': 'references',
         'source': 'source',
         'googleAnalyticsTrackingCode': 'GoogleAnalyticsTrackingCode',
         'license': 'license',
         'keywords': 'keywords',
         }

ATOMPUB_CONTENT_TYPES = ['application/atom+xml',
                         'application/atom+xml;type=entry',
                        ]

def getHeader(request, name, default=None):
    """ Work around the change from get_header to getHeader in a way that will
        survive deprecation of the former. """
    return getattr(request, 'getHeader', request.get_header)(
        name, default)

class IAtomPubService(Interface):
    """ Marker interface for AtomPuv service """

class IAtomFeed(Interface):
    """ Marker interface for AtomPub statement """


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
        content_type = getHeader(self.request, 'content-type').strip(';')
        if content_type in ATOMPUB_CONTENT_TYPES:
            result = self.atom_entry_document(entry=obj)
            return result
        else:
            result = self.media_entry_representation(entry=obj)
            return result

        return 'Nothing to do'
    

    def getContent(self, item):
        if item.portal_type == 'File':
            return item.getFile().data
        return getattr(item, 'rawText', None)


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
        self.response = request.response
        self.ATOMPUB_CONTENT_TYPES = ATOMPUB_CONTENT_TYPES


    def generateFilename(self, name):
        """ The filename as per the Content-Disposition header is passed
            as the name parameter. This method needs to return a save
            name that can be used as the id of the object. """
        # If no name, generate one, otherwise just make sure its safe
        plone_utils = getToolByName(self.context, 'plone_utils')
        if name is None:
            content_type = getHeader(self.request, 'content-type').strip(';')
            safe_name = plone_utils.normalizeString(content_type)
            return self.context.generateUniqueId(type_name=safe_name)
        else:
            return plone_utils.normalizeString(name)


    def __call__(self):
        content_type = getHeader(self.request, 'content-type').strip(';')
        disposition = getHeader(self.request, 'content-disposition')
        slug = getHeader(self.request, 'slug')
        filename = None
        if slug is not None:
            filename = slug
        elif disposition is not None:
            try:
                filename = [x for x in disposition.split(';') \
                    if x.strip().startswith('filename=')][0][10:]
            except IndexError:
                pass

        filename = self.generateFilename(filename)
        obj = self.createObject(self.context, filename, content_type, self.request)
        obj = self.updateObject(
                obj, filename, self.request, self.response, content_type)
        return obj
   

    def createObject(self, context, name, content_type, request):
        if int(request.get('CONTENT_LENGTH', 0)) > LARGE_FILE_THRESHOLD:
            file = request['BODYFILE']
            body = file.read(LARGE_FILE_THRESHOLD)
            file.seek(0)
        else:
            body = request.get('BODY', '')

        registry = getToolByName(context, 'content_type_registry')
        typeObjectName = registry.findTypeName(name, content_type, body)
        context.invokeFactory(typeObjectName, name)
        obj = context._getOb(name)
        return obj


    def updateObject(self, obj, filename, request, response, content_type):
        # fix the request headers to get the correct metadata mappings
        if content_type in ATOMPUB_CONTENT_TYPES:
            request = self._updateRequest(request)
        obj.PUT(request, response)
        obj.setTitle(request.get('Title', filename))
        obj.reindexObject(idxs='Title')
        return obj

    
    def _updateRequest(self, request):
        """ The body.seek(0) looks funny, but I do that to make sure I get
            all the content, no matter who accessed the body file before me.
        """
        # then we update the body of the request
        body = request.get('BODYFILE')
        # update headers from the request body
        # make sure we read from the beginning
        body.seek(0)
        dom = parse(body)

        title = self.getValueFromDOM('title', dom)
        request['Title'] = title
        headers = self.getHeaders(dom, METADATA_MAPPING)
        header = formatRFC822Headers(headers)
        content = self.getValueFromDOM('content', dom)
        # make sure content is not None
        content = content and content or ''
        data = '%s\n\n%s' % (header, content.encode('utf-8'))
        length = len(data)
        request['Content-Length'] = length
        body_file = StringIO(data)
        request['BODYFILE'] = body_file
        return request

   
    def getHeaders(self, dom, mappings): 
        headers = []
        for prefix, uri in dom.documentElement.attributes.items():
            for name in mappings.keys():
                value = dom.getElementsByTagNameNS(uri, name)
                value = '\n'.join([str(v.firstChild.nodeValue).strip() for v in value \
                                   if v.firstChild is not None]
                                 )
                if value: headers.append((mappings[name], str(value)))
        return headers


    def getValueFromDOM(self, name, dom):
        value = None
        elements = dom.getElementsByTagName(name)
        if elements:
            value = elements and elements[0].firstChild.nodeValue or None
        return value


class AtomFeed(BrowserView):
    """ Supporting methods for the atom.pt page template.
    """
    implements(IAtomFeed)


    def __init__(self, context, request):
        super(AtomFeed, self).__init__(context, request)
        self.ps = getToolByName(self.context, "portal_syndication")


    def isSyndicationAllowed(self):
        """ Check whether syndication is allowed in this context.
        """
        return self.ps.isSyndicationAllowed(self.context)


    def syndicatableContent(self):
        return self.ps.getSyndicatableContent(self.context)


    def updateBase(self):
        """Return the date of the last update in HTML4 form as a string"""
        return self.ps.getHTML4UpdateBase(self.context)
