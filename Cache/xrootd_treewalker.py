#!/usr/bin/env python
#---------------------------------------------------------------------------------------------------
# Example to find all files in a given directory on a given site.
#---------------------------------------------------------------------------------------------------
import re,sys
import XRootD.client

user_dir_regexp = re.compile(r'^/+user/+([A-Za-z0-9.]+)/*$')

def process_dir(base_url, directory):
    # process a given directory using a xrootd access point

    fs = XRootD.client.FileSystem(base_url)

    worklist = [directory]
    filelist = []
    failed_list = []
    base_len = len(directory)

    while worklist:
        cwd = worklist.pop()

        if user_dir_regexp.match(cwd):
            cwd += "/public"

        # remove duplicated '/' for cleansiness
        cwd = re.sub('/+','/',cwd)

        # say which directory we are probing
        print "Processing", cwd
        status, dirlist = fs.dirlist("/" + cwd,flags=XRootD.client.flags.DirListFlags.STAT)

        if status.status:
            print "Failed to list directory:", cwd
            failed_list.append("/" + cwd)
            continue

        for entry in dirlist.dirlist:
            if entry.statinfo.flags & XRootD.client.flags.StatInfoFlags.IS_DIR:
                worklist.append(cwd + "/" + entry.name)
            else:
                fname = cwd + "/" + entry.name
                filelist.append((fname[base_len:], entry.statinfo.size))

    print status

    return filelist, failed_list

#--------------------------------------------------------------------------------------------------
#  M A I N
#--------------------------------------------------------------------------------------------------

# LAST CHARACTER IN THE DIR HAS TO BE A   '/'

if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser()

    parser.add_argument('--sitename', '-s', metavar='SiteName', dest='sitename', default=os.environ.get('site'),
                        help='Name of site to run treewalker on.')
    parser.add_argument('--baseurl', '-b', metavar='BaseURL', dest='baseurl', default=os.environ.get('SE_' + os.environ.get('site')),
                        help='Base URL to check with xrootd.')

base_url = 'root://srm.unl.edu//'
dirs = [ '/store/test/xrootd/T2_US_Nebraska/store/data/Run2015E/JetHT/' ] # just testing
# [ '/store/test/xrootd/T2_US_Nebraska/store/data/', '/store/test/xrootd/T2_US_Nebraska/store/mc/' ]

for dir in dirs:

    filelist = process_dir(base_url,dir)
    print '\n =-=-=-= Listing: ' + dir
    print filelist