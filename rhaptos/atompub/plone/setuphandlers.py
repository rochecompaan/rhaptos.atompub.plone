from Products.CMFCore.utils import getToolByName

def setupVarious(context):

    # Ordinarily, GenericSetup handlers check for the existence of XML files.
    # Here, we are not parsing an XML file, but we use this text file as a
    # flag to check that we actually meant for this import step to be run.
    # The file is found in profiles/default.

    if context.readDataFile('rhaptos.atompub.plone_various.txt') is None:
        return

    # Add additional setup code here
    site = context.getSite()
    ctr = getToolByName(site, 'content_type_registry')
    ids = ctr.predicate_ids
    if 'atom+xml' not in ids:
        ctr.addPredicate('atom+xml', 'major_minor')
    ctr.reorderPredicate('atom+xml', 0)
