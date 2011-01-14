'''
File: exceptions.py
Author: Nathan Hoad
Description: contains all exceptions
'''


class ShutdownException(Exception):
    """ShutdownException is a means of signalling to the main process
    that a module has had a fatal error. The exitcode determines the
    application's exit code.

    """
    def __init__(self, exitcode=0):
        super(ShutdownException, self).__init__()
        self.exitcode = exitcode
