"""
Tools to get the files located at a site.

.. Warning::

   Must be used on a machine with xrdfs installed.

:author: Daniel Abercrombie <dabercro@mit.edu>
"""


import re
import os
import time
import datetime
import subprocess
import logging
import random

from . import config
from . import datatypes

LOG = logging.getLogger(__name__)

def get_site_tree(site):
    """
    Get the information for a site, either from a cache or from XRootD.

    :param str site: The site name
    :returns: The site information
    :rtype: DirectoryInfo
    """

    # Get the redirector for a site
    # The redirector is used for a double check (not implemented yet...)
    # The redir_list is used for the original listing

    _, redir_list = config.get_redirector(site)
    LOG.info('Full redirector list: %s', redir_list)

    # Get the primary list of servers to hammer
    primary_list = random.sample(redir_list, (len(redir_list) + 1)/2)
    LOG.info('Primary redirector list: %s', primary_list)

    # Create the filler function for the DirectoryInfo

    error_code_re = re.compile(r'\[(\!|\d+|FATAL)\]')

    def ls_directory(path, attempts=0, prev_stdout='', failed_list=None):
        """
        Gets the contents of the previously defined redirector at a given path

        :param str path: The full path starting with ``/store/``.
        :param int attempts: The number of previous attempts.
                             If the total number of attempts is more than the
                             NumberOfRetries in the config, give back a new dummy file.
                             The young age should lead to the directory being left alone.
        :param str prev_stdout: stdout from previous attempt
        :param list failed_list: A list of redirectors that have not worked
                                 for the current path.
        :returns: A list of directories and list of file information
        :rtype: tuple
        """

        track_failed_list = failed_list or []

        LOG.debug('Calling ls_directory with: path=%s, attempts=%i, '
                  'prev_stdout lines=%i, failed_list=%s', path, attempts,
                  len([line for line in prev_stdout.split('\n') if line.strip()]),
                  track_failed_list)

        # Get a redirector. First try the primary list, unless all primaries are in the failed list
        if len(track_failed_list) < len(primary_list):
            in_list = primary_list
        # If retrying, reset the failed list and get redirector
        elif attempts < config.config_dict().get('NumberOfRetries', 0):
            track_failed_list = []
            attempts += 1
            in_list = primary_list
        # Otherwise, use the full list
        else:
            in_list = redir_list

        valid_redirs = [server for server in in_list if server not in track_failed_list]
        LOG.debug('List of valid redirectors: %s', valid_redirs)
        redirector = random.choice(valid_redirs)

        LOG.debug('Using redirector %s', redirector)
        # This should maybed be configurable
        time.sleep(attempts * 5)

        directory_listing = subprocess.Popen(['xrdfs', redirector, 'ls', '-l', path],
                                             stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE)

        directories = []
        files = []

        stdout, stderr = directory_listing.communicate()

        # Parse the stderr
        if stderr:
            LOG.warning('Received error while listing %s', path)
            LOG.warning(stderr.strip())
            stdout += '\n' + prev_stdout

            track_failed_list.append(redirector)

            # If full number of attempts haven't been made, try again
            if len(track_failed_list) < len(redir_list):
                # Check against list of "error codes" to retry
                error_code = error_code_re.search(stderr).group(1)

                # I should actually raise an exception here
                if error_code in ['!', '3005']:
                    return ('_retry_', (path, attempts, stdout, track_failed_list))

            else:
                LOG.error('Giving up on listing directory %s', path)
                files.append(('_unlisted_', 0, 0))

        # Parse the stdout, skipping blank lines

        LOG.debug('STDOUT:\n%s', stdout)

        for line in [check for check in stdout.split('\n') if check.strip()]:

            # Ignore duplicate lines (which come up a lot)
            elements = line.split()

            if len(elements) != 5:
                LOG.error('Number of elements unexpected: %i', len(elements))
                LOG.error('xrdfs %s ls -l %s', redirector, path)
                LOG.error(stdout)

            # Get the basename only
            name = elements[-1].split('/')[-1]

            # Parse the time in the output to get timestamp
            mtime = int(
                time.mktime(
                    datetime.datetime.strptime(
                        '%s %s' % (elements[1], elements[2]),
                        '%Y-%m-%d %H:%M:%S').timetuple()
                    )
                )

            # Determine if directory or file
            if elements[0][0] == 'd':
                directories.append((name, mtime))
            else:
                # For files, append tuple (name, size, mtime)
                files.append((name, int(elements[-2]), mtime))

        LOG.debug('From %s returning %i directories and %i files.',
                  path, len(directories), len(files))

        LOG.debug('OUTPUT:\n%s\n%s', directories, files)
        return directories, files

    # Create DirectoryInfo for each directory to search
    directories = [
        datatypes.create_dirinfo('/store/', directory, ls_directory) for \
            directory in config.config_dict().get('DirectoryList', [])
        ]

    # Merge the DirectoryInfo
    info = datatypes.DirectoryInfo(name='/store', to_merge=directories)
    info.setup_hash()

    # Save
    info.save(os.path.join(config.config_dict()['CacheLocation'],
                           '%s_remotelisting.pkl' % site))

    # Return the DirectoryInfo
    return info
