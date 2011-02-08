#!/usr/bin/python
import re
import sys

search = re.compile(r'send (\S+)', re.IGNORECASE)
result = search.search(sys.argv[4])

if result:
    filename = result.groups()[0]
    filename.replace('\r', '')
    filename.replace('\n', '')
    print('attach_file {0}'.format(result.groups()[0]))
