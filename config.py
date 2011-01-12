'''
File: config.py
Author: Nathan Hoad
Description: Simple ini-file like config parser
'''

import os
import re

class Config(dict):
    """Config class to handle ini files"""
    file_found = False

    def __init__(self):
        super(Config, self).__init__()
        return None

    def read(self, file_name):
        if os.path.isfile(file_name):
            self.file_found = True
        else:
            return False

        if len(self) > 0:
            print("clearing")
            self.clear()

        section_pattern = re.compile('^\[\S+\]$')
        conf = open(file_name, 'r')
        section = ""

        for line in conf.readlines():
            line = line.strip()
            if line:
                if section_pattern.search(line):
                    section = line[1:-1]
                    self[section] = {}
                else:
                    line = line.split("=")
                    key = line[0].strip()
                    value = " ".join(line[1:]).strip()
                    self[section][key] = value
        return True

    def __bool__(self):
        return self.file_found
