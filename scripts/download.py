#!/usr/bin/python2
import sys, os
import errno
import urllib
import re
from threading import Thread

save_location = os.path.normpath(os.environ['HOME'] + "/Downloads")
search_pattern = r'((https?://|www.)?[.\S]+)'

class DownloadThread(Thread):
    """Thread to download a file. """
    def __init__(self, link, save_path):
        Thread.__init__(self)

        self.link = link
        self.save_path = save_path

    def run(self):
        filename = os.path.basename(self.link)
        file_path = os.path.join(self.save_path, filename)
        try:
            urllib.urlretrieve(self.link, file_path)
            print "SUCCESS: %s" % self.link

        except IOError, e:
            if e.errno == errno.ENOENT:
                print "ERROR: Could not save %s" % self.link

if __name__ == "__main__":

    links = re.findall(search_pattern, sys.argv[4])

    for link in links:
        DownloadThread(link[0], os.path.join(os.environ['HOME'], "Downloads")).start()
