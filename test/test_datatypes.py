#! /usr/bin/env python

"""
Jobs of datatypes:

- Define a tree type that can be quickly compared with other trees
- Save the tree without data loss
- Remote listing and using a local list to check consistency
- In the tree, files that are too new should not affect the comparison

Things to test:

x Save and load trees and compare them to trees only in memory
x Creation of tree through list of files and through a filler function
  and compare them to see if they're the same
x Create two different trees and make sure the differences noted are correct
x Create new files and see if they affect the hash
x Create multiple trees and merge them
x Identifies empty directories to be removed
x Test size to clear
x Ignores directories that are too new

This is the development test script. Please don't touch if you're not me.
"""

import os
import sys
import time
import shutil
import unittest
import logging

from ConsistencyCheck import config
from ConsistencyCheck import datatypes

TMP_DIR = 'TempConsistency'
LOG = logging.getLogger(__name__)

# Define a filler function to use in the "remote filling" test
def my_ls(path, location=TMP_DIR):

    full_path = os.path.join(location, path)
    results = [os.path.join(full_path, res) for res in os.listdir(full_path)]

    dirs  = [(os.path.basename(name), os.stat(name).st_mtime) for \
                 name in filter(os.path.isdir, results)]
    files = [(os.path.basename(name), os.stat(name).st_size, os.stat(name).st_mtime) for \
                 name in filter(os.path.isfile, results)]

    return True, dirs, files

class TestBase(unittest.TestCase):

    tree = None
    tmpdir = None

    file_list = [
        ('/store/mc/ttThings/0000/qwert.root', 20),
        ('/store/mc/ttThings/0000/qwery.root', 30),
        ('/store/mc/ttThings/0001/zxcvb.root', 50),
        ('/store/mc/ttThings/0000/doulb.root', 30),
        ('/store/data/runB/0001/missi.root', 45),
        ('/store/data/runB/earlyfile.root', 5),
        ('/store/data/runA/0030/stuff.root', 10),
        ]

    def setUp(self):
        if os.path.exists(TMP_DIR):
            print 'Desired directory location already exists!'
            exit(1)
        os.makedirs(TMP_DIR)
        self.tree = datatypes.DirectoryInfo('/store')
        self.tree.add_file_list(self.file_list)
        self.do_more_setup()

    def tearDown(self):
        if os.path.exists(TMP_DIR):
            shutil.rmtree(TMP_DIR)

    def do_more_setup(self):
        pass

    def check_equal(self, tree0, tree1):

        tree0.setup_hash()
        tree1.setup_hash()

        self.assertEqual(tree0.hash, tree1.hash,
                         '%s\n=\n%s' % (tree0.displays(), tree1.displays()))
        self.assertEqual([fi['hash'] for fi in tree0._grab_first().files],
                         [fi['hash'] for fi in tree1._grab_first().files])
        self.assertEqual(tree0.get_num_files(), tree1.get_num_files())
        self.assertEqual(tree0.get_num_files(True), tree1.get_num_files(True))

class TestTree(TestBase):

    def test_num_files(self):
        self.assertEqual(self.tree.get_num_files(),
                         len(self.file_list))
        self.assertEqual(self.tree.get_num_files(True), 0)

    def test_do_hash(self):
        self.assertFalse(self.tree.hash)
        self.tree.setup_hash()
        self.assertTrue(self.tree.hash)

    def test_compare_saved(self):
        self.tree.save(os.path.join(TMP_DIR, 'tree.pkl'))
        tree0 = datatypes.get_info(os.path.join(TMP_DIR, 'tree.pkl'))

        self.check_equal(self.tree, tree0)

    def test_empty_compare(self):
        file_list, dir_list, size = self.tree.compare(None)

        self.assertEqual(len(file_list), len(self.file_list))
        self.assertEqual(len(dir_list), 0)
        self.assertEqual(size, sum([size for _, size in self.file_list]))

    def test_merge_trees(self):
        trees = {
            'mc': datatypes.DirectoryInfo('mc'),
            'data': datatypes.DirectoryInfo('data')
            }

        for key, tree in trees.iteritems():
            tree.add_file_list([('/'.join(name.split('/')[2:]), size) \
                                    for name, size in self.file_list if name.split('/')[2] == key])

        one_tree = datatypes.DirectoryInfo('/store', [trees['data'], trees['mc']])
        self.check_equal(self.tree, one_tree)

        # Hopefully order doesn't matter

        two_tree = datatypes.DirectoryInfo('/store', [trees['mc'], trees['data']])
        self.check_equal(self.tree, two_tree)
        self.check_equal(one_tree, two_tree)

class TestConsistentTrees(TestBase):

    def do_more_setup(self):
        for name, size in self.file_list:
            path = os.path.join(TMP_DIR, name[7:])
            if not os.path.isdir(os.path.dirname(path)):
                os.makedirs(os.path.dirname(path))
            out = open(path, 'w')
            out.write('\0' * size)
            out.close()

            os.utime(path, (1000000000, 1000000000))

    def test_ls_vs_list(self):

        dirinfos = [datatypes.create_dirinfo('', subdir, my_ls) \
                        for subdir in ['mc', 'data']]

        master_dirinfo = datatypes.DirectoryInfo('/store', to_merge=dirinfos)

        self.check_equal(self.tree, master_dirinfo)
        self.assertEqual(self.tree.count_nodes(), master_dirinfo.count_nodes())

    def test_newdir(self):
        empty_dir = 'mc/new/empty/0002'

        os.makedirs(os.path.join(TMP_DIR, empty_dir))

        dirinfos = [datatypes.create_dirinfo('', subdir, my_ls) \
                        for subdir in ['mc', 'data']]

        master_dirinfo = datatypes.DirectoryInfo('/store', to_merge=dirinfos)

        self.check_equal(self.tree, master_dirinfo)
        self.assertFalse(master_dirinfo.get_node(os.path.join(empty_dir, 'not_there'), False))
        self.assertTrue(master_dirinfo.get_node(empty_dir, False))
        self.assertFalse(master_dirinfo.get_node(empty_dir, False).can_compare)


class TestInconsistentTrees(TestBase):

    listing = None

    orphan = [
        ('/store/data/runE/0000/toomany.root', 20)
        ]
    missing = [
        ('/store/mc/Zllll/0023/signal.root', 15)
        ]
    new_file = [
        ('/store/data/runQ/0000/recent.root', 10)
        ]

    def do_more_setup(self):
        for name, size in self.file_list + self.orphan:
            path = os.path.join(TMP_DIR, name[7:])
            if not os.path.isdir(os.path.dirname(path)):
                os.makedirs(os.path.dirname(path))
            out = open(path, 'w')
            out.write('\0' * size)
            out.close()

            os.utime(path, (1000000000, 1000000000))

        self.tree.add_file_list(self.missing)

        for name, size in self.new_file:
            path = os.path.join(TMP_DIR, name[7:])
            if not os.path.isdir(os.path.dirname(path)):
                os.makedirs(os.path.dirname(path))
            out = open(path, 'w')
            out.write('\0' * size)
            out.close()

        self.listing = datatypes.DirectoryInfo(
            '/store', to_merge=[datatypes.create_dirinfo('', subdir, my_ls) \
                                    for subdir in ['mc', 'data']])

        self.tree.setup_hash()
        self.listing.setup_hash()

    def test_orphan(self):
        file_list, dir_list, _ = self.listing.compare(self.tree)

        self.assertEqual(len(file_list), 1)
        self.assertEqual(file_list[0], self.orphan[0][0])

    def test_missing(self):
        file_list, dir_list, _ = self.tree.compare(self.listing)

        self.assertEqual(len(file_list), 1)
        self.assertEqual(file_list[0], self.missing[0][0])

    def test_both(self):
        file_base = os.path.join(TMP_DIR, 'report')
        datatypes.compare(self.tree, self.listing, file_base)

        with open('%s_missing.txt' % file_base, 'r') as missing_file:
            missing = missing_file.readlines()

        with open('%s_orphan.txt' % file_base, 'r') as orphan_file:
            orphan = orphan_file.readlines()

        self.assertEqual(len(missing), 1)
        self.assertEqual(len(orphan), 1)

        self.assertEqual(missing[0].strip(), self.missing[0][0])
        self.assertEqual(orphan[0].strip(), self.orphan[0][0])

    def test_olddir(self):
        empty_dir = 'mc/new/empty/0002'
        path = os.path.join(TMP_DIR, empty_dir)
        os.makedirs(path)
        os.utime(path, (1000000000, 1000000000))

        listing = datatypes.DirectoryInfo('/store',
                                          to_merge=[datatypes.create_dirinfo('', subdir, my_ls) for
                                                    subdir in ['mc', 'data']])

        LOG.info('='*40)
        LOG.info('Doing the hash')
        LOG.info('='*40)

        listing.setup_hash()

        LOG.info('='*40)
        LOG.info('Doing the comparison')
        LOG.info('='*40)

        LOG.info(listing.displays())
        LOG.info('='*40)
        LOG.info(self.listing.displays())

        file_list, dir_list, _ = listing.compare(self.listing)

        self.assertEqual(len(dir_list), 1)
        self.assertTrue(os.path.join('/store', empty_dir).startswith(dir_list[0]))

        for file_name, _ in self.file_list:
            self.assertFalse(file_name.startswith(dir_list[0]))

    def test_new_file(self):
        self.tree.add_file_list(self.orphan)
        self.listing.add_file_list(self.missing)

        self.assertNotEqual(self.tree.get_num_files(), self.listing.get_num_files())
        self.assertEqual(self.tree.get_num_files() + len(self.new_file),
                         self.listing.get_num_files())

        self.tree.setup_hash()
        self.listing.setup_hash()

        self.assertEqual(self.tree.hash, self.listing.hash,
                         '%s\n=\n%s' % (self.tree.displays(), self.listing.displays()))

    def test_same_dir(self):
        self.tree.add_file_list(self.orphan)
        self.listing.add_file_list(self.missing)

        same_dir = [('/store/data/runB/0001/misso.root', 35)]

        self.tree.add_file_list(same_dir)

        self.listing.setup_hash()
        self.tree.setup_hash()

        LOG.info('=' * 30)
        LOG.info('Building done, going to compare')
        LOG.info('=' * 30)

        file_list, dir_list, _ = self.tree.compare(self.listing)

        self.assertFalse(dir_list)
        self.assertTrue(file_list)
        self.assertEqual(len(file_list), 1)
        self.assertEqual(file_list[0], same_dir[0][0])

if __name__ == '__main__':

    if len(sys.argv) > 1:
        logging.basicConfig(level=logging.DEBUG)

    unittest.main()
