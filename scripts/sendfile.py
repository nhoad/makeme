#!/usr/bin/python
import re
import sys

search = re.compile(r'send (\S+)', re.IGNORECASE)
result = search.search(sys.argv[4])

restricted_names = ['makemerc', '.makemerc']

if result:
    filename = result.groups()[0]
    filename.replace('\r', '')
    filename.replace('\n', '')

    # prevent the user from sending the config file to themselves.
    if filename not in restricted_names:
        print('attach_file {0}'.format(filename)
