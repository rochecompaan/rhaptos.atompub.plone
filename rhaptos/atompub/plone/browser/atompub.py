from copy import copy
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

from Products.Archetypes.Marshall import formatRFC822Headers

from rhaptos.atompub.plone.interfaces import IAtomPubServiceAdapter

METADATA_MAPPING = {'title': 'Title',
                    'sub': 'Subject',
                    'subject': 'Subject',
                    'publisher': 'Publisher',
                    'description': 'Description',
                    'creators': 'Creators',
                    'effective_date': 'effective_date',
                    'expiration_date': 'expiration_date',
                    'type': 'Type',
                    'format': 'Format',
                    'language': 'Language',
                    'rights': 'Rights',
                    'accessRights': 'accessRights',
                    'rightsHolder': 'rightsHolder',
                    'abstract': 'abstract',
                    'alternative': 'alternative',
                    'available': 'available',
                    'bibliographicCitation': 'bibliographicCitation',
                    'contributor': 'Contributors',
                    'hasPart': 'hasPart',
                    'hasVersion': 'hasVersion',
                    'identifier': 'identifier',
                    'isPartOf': 'isPartOf',
                    'references': 'references',
                    'source': 'source',
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
        self.response = request.response


    def __call__(self):
        content_type = self.request.getHeader('content-type').strip(';')
        disposition = self.request.getHeader('content-disposition')
        filename = None
        if disposition is not None:
            try:
                filename = [x for x in disposition.split(';') \
                    if x.strip().startswith('filename=')][0][10:]
            except IndexError:
                pass

        # If no filename, make one up, otherwise just make sure its http safe
        if filename is None:
            safe_filename = self.context.generateUniqueId(
                    type_name=self._getPrefix(content_type))
        else:
            safe_filename = getToolByName('plone_utils').normalizeString(filename)

        # fix the request headers to get the correct metadata mappings
        request = self._updateRequest(self.request, content_type)

        nullresource = NullResource(self.context, safe_filename, request)
        nullresource = nullresource.__of__(self.context)
        nullresource.PUT(request, self.response)

        # Look it up and finish up, then return it.
        obj = self.context._getOb(safe_filename)
        obj.PUT(request, self.response)
        obj.setTitle(request.get('Title', safe_filename))
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

            content = self.getValueFromDOM('content', dom)
            title = self.getValueFromDOM('title', dom)
            request['Title'] = title
            headers = self.getHeaders(
                    dom, self.getMetadataMapping(METADATA_MAPPING, dom)
                    )
            header = formatRFC822Headers(headers)
            data = '%s\n\n%s' % (header, content.encode('utf-8'))
            length = len(data)
            request['Content-Length'] = length
            body_file = StringIO(data)
            request['BODYFILE'] = body_file
        return request

   
    def getMetadataMapping(self, base_mapping, dom):
        attrs = dom.documentElement.attributes.keys()
        name_space_prefixes = []
        for attr in attrs:
            split_attr = attr.split(':')
            if len(split_attr) > 1:
                extension = split_attr[1]
                name_space_prefixes.append(extension)
        
        mappings = {}
        for prefix in name_space_prefixes:
            tmp_dict = copy(base_mapping)
            for key, value in tmp_dict.items():
                mappings['%s:%s' %(prefix, key)] = value
        return mappings 


    def getHeaders(self, dom, mappings): 
        headers = []
        for name in mappings.keys():
            value = dom.getElementsByTagName(name)
            value = '\n'.join([str(v.firstChild.nodeValue) for v in value \
                               if v.firstChild is not None]
                             )
            headers.append((mappings[name], str(value)))
        return headers


    def getValueFromDOM(self, name, dom):
        value = None
        elements = dom.getElementsByTagName(name)
        if elements:
            value = elements and elements[0].firstChild.nodeValue or None
        return value


    def _getPrefix(self, seed):
        tmp_name = seed.replace('/', '_')
        tmp_name = tmp_name.replace('+', '_')
        tmp_name = tmp_name.strip(';')
        return tmp_name
