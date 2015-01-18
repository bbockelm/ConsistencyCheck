import os,json
import deco

def CheckDir(tempPrefix,prefix):
    print 'Checking out ' + tempPrefix
    if os.path.isdir(tempPrefix+'/store'):                      # Check that this prefix directory exists
        if len(os.listdir(tempPrefix+'/store')) > 0:            # Check that it is not empty
            print 'Contents of Prefix + /store'
            print os.listdir(tempPrefix+'/store')
            perhaps = False
            for term in os.listdir(tempPrefix+'/store'):
                if term == 'mc' or term == 'data':
                    print 'This looks promising...'
                    perhaps = True
            if prefix != tempPrefix and perhaps:
                if prefix != '':
                    print prefix + ' changing to ' + tempPrefix
                    print 'I hope that\'s right...'
                ##
                return True
    ##
    return False
                    
def GetPrefix(TName):
    tfcFile = open(TName + '_tfc.json')
    tfcData = json.load(tfcFile, object_hook = deco._decode_dict)            # This converts the unicode to ASCII strings (see deco.py)
    tfcFile.close()

    tfcPaths = []
    tfcNames = []

    print 'Converting LFN to PFN...'

    for check in tfcData['phedex']['storage-mapping']['array']:              # This is basically just checking that the TFC has an entry I understand
        if check['protocol'] == 'direct' and check['element_name'] == 'lfn-to-pfn':
            print check
            tfcPaths.append(check['result'])
#            tfcNames.append(check['path-match'])
        print "tfcPaths:"
        print tfcPaths
    ##
    prefix = ''
    for tfcPath in tfcPaths:
        tempPrefix = tfcPath.split('$1')[0].split('store')[0].rstrip('/')    # Get the temporary prefix to check
        if CheckDir(tempPrefix,prefix):
            prefix = tempPrefix
    ##
    if prefix == '':
        print 'ERROR: Problem with the TFC.'                                 # If not found yet, I give up
        exit()
    ##
    return prefix
