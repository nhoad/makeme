'''
File: threads.py
Author: Nathan Hoad
Description: Contains all Thread classes for processing emails.
'''

import logging
import os

from threading import Thread
from subprocess import Popen, PIPE

import emails


class MessageProcessThread(Thread):
    """Thread for processing a message and replying accordingly."""
    def __init__(self, message, patterns, sender):
        Thread.__init__(self)

        self.message = message
        self.patterns = patterns
        self.sender = sender

    def run(self):
        """React accordingly."""
        for pattern in tuple(self.patterns.keys()):
            if self.message.search(pattern):
                logging.info("executing {0}"\
                    .format(self.patterns[pattern]))

                command = [os.path.normpath(\
                    os.getcwd() + "/scripts/" + self.patterns[pattern])]
                command.append(self.message.sender)
                command.append(self.message.receiver)
                command.append(self.message.subject)
                command.append(self.message.body)

                pipe = Popen(command, shell=True, bufsize=-1, \
                    stdout=PIPE, stderr=PIPE)

                pipe.wait()
                logging.debug("Popen for {0} complete".format(command))
                # stderr is the "script"
                self.script = str(pipe.stderr.read(), encoding='utf8')
                # send stdot
                self.reply_message = str(pipe.stdout.read(), encoding='utf8')

                if not self.process_script():
                    self.process_message()

                return

    # TODO complete this method
    def process_script(self):
        """docstring for process_script"""
        return False

    def process_message(self):
        """docstring for process_message"""
        to = self.message.sender
        subject = "RE: {0}".format(self.message.subject)
        body = self.reply_message
        self.sender.send_email(emails.Email(receiver=to, subject=subject, body=body))


class ProcessThreadsStarter(Thread):
    """Thread for starting a MessageProcessThread for each email.
    Prevents the main program flow from becoming too blocked

    """
    def __init__(self, server, patterns):
        Thread.__init__(self)
        self.server = server
        self.patterns = patterns

    def run(self):
        self.messages = self.server.receive_mail()

        if len(self.messages) == 0:
            logging.info("No instructions were received!")
        for message in self.messages:
            MessageProcessThread(message, self.patterns, self.server).start()

        self.server.logout_imap()
