'''
File: threads.py
Author: Nathan Hoad
Description: Contains all Thread classes for processing emails.
'''

import logging
import os

import threading
from threading import Thread
from subprocess import Popen, PIPE
from smtplib import SMTPServerDisconnected
import re

from emails import Email
import config


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
                    self.sender.add_email_to_queue(Email(receiver=to, subject=subject, body=body))

                self.lock.release()

                return

    def process_script(self):
        """Process the standard output for any scripting commands to be handled."""
        if len(self.script) == 0:
            return False

        to = self.message.sender
        subject = "RE: {0}".format(self.message.subject)
        body = self.reply_message

        email = Email(receiver=to, subject=subject, body=body)

        attach_pattern = re.compile(r'attach_file (\S+)', re.IGNORECASE)
        reply_pattern = re.compile(r'change_reply_address (\S+)', re.IGNORECASE)

        for line in self.script.split('\n'):
            result = attach_pattern.search(line)
            if result:
                email.attach_file(result.groups()[0])
            else:
                result = reply_pattern.search(line)
                if result:
                    email.receiver  = result.groups()[0]

        self.sender.send_email(email)
        return True

    def process_message(self):
        """Process the stanard error for all output to be sent back to the user."""
        to = self.message.sender
        subject = "RE: {0}".format(self.message.subject)
        body = self.reply_message
        self.sender.send_email(Email(receiver=to, subject=subject, body=body))


class ProcessThreadsStarter(Thread):
    """Thread for starting a MessageProcessThread for each email.

    Prevents the main program flow from becoming too blocked

    """
    def __init__(self, server, patterns):
        Thread.__init__(self)
        self.server = server
        self.patterns = patterns
        self.name = "ProcessThreadStarter"
        self.lock = self.server.lock
        self.children = []

    def run(self):
        """Checks the server for messages, and if it finds any it creates a MessageProcessThread for each email"""

        # make sure only one ProcessThreadStarter is running at a time.
        for t in threading.enumerate():
            if t.name == self.name and self != t:
                return

        self.messages = None

        self.lock.acquire()

        # +1 because the first time isn't really an attempt.
        for i in range(self.server.reconnect_attempts + 1):
            try:
                self.messages = self.server.receive_mail()
                break
            except smtplib.SMTPServerDisconnected as e:
                if i == self.server.reconnect_attempts:
                    logging.critical('Could not connect to the IMAP server!')
                    raise ShutdownException(10)
                time.sleep(30)
                continue

        self.lock.release()

        if len(self.messages) == 0:
            logging.info("No instructions were received!")

        for message in self.messages:
            new_thread = MessageProcessThread(message, self.patterns, self.server, self.lock)
            new_thread.start()

            # let's store only threads this thread creates, for sanity later on
            self.children.append(new_thread)

        self.server.logout_imap()

        # let's wait for all our child threads to finish. The old code waited
        # for _every_ thread except ones specified to finish. This is much
        # more flexible in regards to changes.
        for f in self.children:
            if f.is_alive():
                f.join()

        # TODO: this should handle unsent emails much tidier. If it can't manage to log in, it should save them to a file.
        if len(self.server.unsent_emails) > 0:
            self.lock.acquire()
            self.server.login_smtp()

            for e in self.server.unsent_emails:
                self.server.send_email(e)

            self.lock.release()
