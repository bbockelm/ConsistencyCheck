"""Small module to get information from the config.

.. Warning::

   Must be used on a machine with xrdfs installed (for locate command).

:author: Daniel Abercrombie <dabercro@mit.edu>
"""


import os
import time
import subprocess
import logging
import json

from CMSToolBox.siteinfo import get_domain

LOG = logging.getLogger(__name__)
CONFIG_FILE = 'consistency_config.json'
"""
The string giving the location of the configuration JSON file.
Generally, you want to set this value of the module before calling
:py:func:`config_dict` to get your configuration.
"""
LOADER = json
"""
A module that uses the load function on a file descriptor to return a dictionary.
(Examples are the ``json`` and ``yaml`` modules.)
If your ``CONFIG_FILE`` is not a JSON file, you'll want to change this
also before calling :py:func:`config_dict`.
"""

def config_dict():
    """
    :returns: the configuration file in a dictionary
    :rtype: str
    :raises IOError: when it cannot find the configuration file
    :raises KeyError: when the CacheDirectory key is not set in the configuration file
    """

    location = CONFIG_FILE
    output = None

    # If not there, fall back to the test directory
    # This is mostly so that Travis-CI finds a configuration on it's own
    if not os.path.exists(location):
        LOG.warning('Could not find file at %s. '
                    'Set the value of config.CONFIG_FILE to avoid receiving this message',
                    location)
        location = os.path.join(os.path.dirname(__file__),
                                'test', CONFIG_FILE)
        LOG.warning('Falling back to test configuration: %s', location)

    # If file exists, load it
    if os.path.exists(location):
        with open(location, 'r') as config:
            LOG.debug('Opening config: %s', location)
            output = LOADER.load(config)
    else:
        raise IOError('Could not load config at ' + location)

    # Overwrite any values with environment variables
    for key in output.keys():
        output[key] = os.environ.get(key, output[key])

    num_threads = os.environ.get('NumThreads', output.get('NumThreads'))
    # If NumThreads is non zero or not none
    if num_threads:
        output['MaxThreads'] = num_threads
        output['MinThreads'] = num_threads

    cache_location = output.get('CacheLocation')

    # Create the directory holding the cache
    if cache_location:
        if not os.path.exists(cache_location):
            os.makedirs(cache_location)
    else:
        raise KeyError('Configuration dictionary does not have a Cache Location set. '
                       'Using dictionary at ' + location)

    return output


def _xrd_locate(redirs, file_name, max_age):
    """
    Dump the redirectors from a xrdfs locate call into a file.
    Only makes the call if the cache is old, or non-existent.
    This is used by :py:func:`get_redirector`.

    :param list redirs: Is a list of redirectors to check for servers
    :param str file_name: Is the name of the file to output the redirector
    :param float max_age: The maximum age of a cached file, in seconds
    """

    # Update, if necessary (File doesn't exist or is too old)
    if not os.path.exists(file_name) or \
            (time.time() - os.stat(file_name).st_mtime) > max_age:

        with open(file_name, 'w') as redir_file:

            for global_redir in redirs:
                # Get the locate from each redirector
                LOG.debug('About to call: %s %s %s', 'xrdfs', global_redir, 'locate -h /store/')
                proc = subprocess.Popen(['xrdfs', global_redir, 'locate', '-h', '/store/'],
                                        stdout=subprocess.PIPE)

                for line in proc.stdout:
                    redir_file.write(line.split()[0] + '\n')

                proc.communicate()


def get_redirector(site):
    """
    Get the redirector and xrootd door servers for a given site.
    An example valid site name is ``T2_US_MIT``.

    :param str site: The site we want to contact
    :returns: Public hostname of the local redirector
              and a list of xrootd door servers
    :rtype: str, list
    """
    LOG.debug('Getting doors for %s', site)
    config = config_dict()
    max_age = config.get('RedirectorAge', 0) * 24 * 3600

    # If the redirector is hardcoded, return it
    redirector = config.get('Redirectors', {}).get(site, '')
    redirs = []

    # If not hard-coded, get the redirector
    if not redirector:
        # First check the cache
        file_name = os.path.join(config['CacheLocation'], 'redirector_list.txt')

        _xrd_locate(['xrootd-redic.pi.infn.it', 'cmsxrootd1.fnal.gov'],
                    file_name, max_age)

        # Parse for a correct redirector
        domain = get_domain(site)
        with open(file_name, 'r') as redir_file:
            for line in redir_file:
                if domain in line:
                    redirs.append(line.strip())

        redirector = redirs[0]
    else:
        redirs.append(redirector)

    # Use that site redirector to get a list of doors
    list_name = os.path.join(config['CacheLocation'], '%s_redirector_list.txt' % site)
    _xrd_locate(redirs, list_name, max_age)
    LOG.debug('Door list cached at %s', list_name)

    # Get the list of doors
    with open(list_name, 'r') as list_file:
        local_list = list(set([line.strip() for line in list_file]))

    LOG.debug('From %s, got list %s', redirector, local_list)

    # Return redirector and list of xrootd doors
    return (redirector, local_list)
