from zope.interface import Interface

class IAtomPubServiceAdapter(Interface):
    """ Marker interface for AtomPubService adapters.
    """

class IAtomFeedProvider(Interface):
    """ Marker interface for Atom feed objects.
    """
