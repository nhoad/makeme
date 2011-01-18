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
        pass

    def read(self, file_name):
        """Read a config file and parse it.
        Returns true if sucessful, false otherwise

        Keyword arguments:
        file_name -- the file to openi and parse

        """
        if os.path.isfile(file_name):
            self.file_name = file_name
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

    def save(self):
        """Save the config to file_name"""
        output = open(self.file_name, 'w')

        for k in self.keys():
            output.write("[{0}]\n".format(k))
            for s in self[k]:
                output.write("{0} = {1}\n".format(s, self[k][s]))

        output.close()


def get_config(user_file, global_file):
    """Return a valid Config class if the files are valid.
    Returns None if no valid configs were found

    Keyword arguments:
    user_file -- path to the user's config file
    global_file -- path to the global configuration file

    """
    c = Config()

    if c.read(user_file):
        return c

    if c.read(global_file):
        return c

    return None
