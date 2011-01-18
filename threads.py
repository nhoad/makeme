'''
File: threads.py
Author: Nathan Hoad
Description: Contains all Thread classes for processing emails.
'''

import logging
import os

from threading import Thread, Lock
from subprocess import Popen, PIPE

from smtplib import SMTPServerDisconnected

import emails


class MessageProcessThread(Thread):
    """Thread for processing a message and replying accordingly."""
    def __init__(self, message, patterns, sender, lock):
        Thread.__init__(self)

        self.message = message
        self.patterns = patterns
        self.sender = sender
        self.lock = lock

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

                pipe = Popen(command, stdout=PIPE, stderr=PIPE)

                pipe.wait()
                logging.debug("Popen for {0} complete".format(command))
                # stdout is the "script"
                self.script = str(pipe.stdout.read(), encoding='utf8')
                # stderr is the reply text in the event an exception occurs.
                self.reply_message = str(pipe.stderr.read(), encoding='utf8')

                self.lock.acquire()

                try:
                    if not self.process_script():
                        self.process_message()
                except SMTPServerDisconnected as e:
                    to = self.message.sender
                    subject = "RE: {0}".format(self.message.subject)
                    body = self.reply_message
                    self.sender.add_email_to_queue(emails.Email(receiver=to, subject=subject, body=body))

                self.lock.release()

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
        self.name = "ProcessThreadStarter"

    def run(self):
        self.messages = self.server.receive_mail()
        self.lock = Lock()

        if len(self.messages) == 0:
            logging.info("No instructions were received!")
        for message in self.messages:
            MessageProcessThread(message, self.patterns, self.server, self.lock).start()

        self.server.logout_imap()

        for f in threading.enumarate():
            if f.name == self.name or f,name == 'MainThread':
                continue

            f.join()

        if len(self.server.email_queue) > 0:
            self.server.login_smtp()

            for e in self.server.email_queue):
                self.server.send_email(e)

