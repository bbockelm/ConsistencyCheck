#! /usr/bin/env python

import os
import sys
import re
import socket
import unittest
import logging
import time

from ConsistencyCheck import getsitecontents
from ConsistencyCheck import datatypes
from ConsistencyCheck import config

def my_ls(path, location='/mnt/hadoop/cms/store'):

    full_path = os.path.join(location, path)

    if not os.path.exists(full_path):
        return [], []

    results = [os.path.join(full_path, res) for res in os.listdir(full_path)]

    dirs  = [(os.path.basename(name), os.stat(name).st_mtime) for \
                 name in filter(os.path.isdir, results)]
    files = [(os.path.basename(name), os.stat(name).st_size, os.stat(name).st_mtime) for \
                 name in filter(os.path.isfile, results)]

    return dirs, files

class TestT3Listing(unittest.TestCase):

    def test_xrd_on_t3(self):

        remote_tree = getsitecontents.get_site_tree('T3_US_MIT')

        local_listing = datatypes.DirectoryInfo(
            '/store', to_merge=[
                datatypes.create_dirinfo('', subdir, my_ls) for \
                    subdir in config.config_dict().get('DirectoryList', [])
                ])

        local_listing.setup_hash()

        print '='*30
        local_listing.display()
        print '='*30
        remote_tree.display()

        self.assertEqual(local_listing.hash, remote_tree.hash)

    def test_compare_inventory(self):
#        remote_tree = getsitecontents.get_site_tree('T3_US_MIT')

        # Make from inventory
        inv_tree = None

if __name__ == '__main__':

    if 'loop' in sys.argv:
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s:%(levelname)s:%(name)s: %(message)s')

        while True:
            getsitecontents.get_site_tree('T3_US_MIT')

    elif len(sys.argv) == 2:
        start = time.time()

        logging.basicConfig(level=logging.DEBUG)

        tree = getsitecontents.get_site_tree(sys.argv[1])
        tree.display()

        print '\nDuration: %f seconds\n' % (time.time() - start)

    else:
        if re.match(r'T3[A-Z]{4}\d{3}.MIT.EDU', socket.getfqdn()):
            unittest.main()
