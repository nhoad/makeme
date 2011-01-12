#!/usr/bin/python2
import sys, os
import errno
import urllib
import re
import transmissionrpc
from threading import Thread

search_pattern = r'((https?://|www.)?[.\S]+)'
server_pattern = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(:(\d{1,5}))?'

port = 9091
server = '192.168.1.75'
should_stop = False

result = re.search(server_pattern, sys.argv[4])

if re.search(r'HALT', sys.argv[4]):
    should_stop = True

if result is not None:
    if len(result.groups()) == 1:
        server = result.groups()[0]
    else:
        server = result.groups()[0]
        port = result.groups()[2]

tc = transmissionrpc.Client(server, port=port)

class DownloadThread(Thread):
    """Thread to download a file. """
    def __init__(self, link):
        Thread.__init__(self)

        self.link = link

    def run(self):
        try:
            id = tc.add_url(self.link).keys()[0]

            if should_stop:
                tc.stop(id)

            print "SUCCESS: %s" % self.link

        except IOError, e:
            if e.errno == errno.ENOENT:
                print "ERROR: Could not save %s" % self.link

links = re.findall(search_pattern, sys.argv[4])

for link in links:
    DownloadThread(link[0]).start()
