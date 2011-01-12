#!/usr/bin/python3
import sys
import os
import re
import signal
import time
import logging
from threading import Thread
from subprocess import Popen, PIPE
from email.parser import HeaderParser
import email
import smtplib
import imaplib

import config


def shutdown(sig=None, func=None):
    logging.info("Shutting down pymote.")
    sys.exit(0)


def get_config(user_file, global_file):
    c = config.Config()

    if c.read(user_file):
        return c

    if c.read(global_file):
        return c

    logging.critical("No .pymoterc file could be found. Check documentation for details.")
    sys.exit(1)


class Email():
    """email wrapper class to make handling emails nicer"""
    def __init__(self, sender, receiver, subject, message):
        self.sender = sender
        self.receiver = receiver
        self.subject = subject
        self.message = message

    def attach_file(self, filename, data):
        self.filename = filename
        self.data = data

    def search(self, pattern):
        """Search the message and subject for pattern, return true or false"""
        return re.search(r'%s' % pattern, self.subject) or re.search(r'%s' % pattern, self.message)


class EmailServer():
    """EmailServer wraps up all the functionality of processing emails and whatnot."""

    message = """From: %s\r\nTo: %s\r\nSubject: %s\r\n%s\r\n"""

    def __init__(self, username, password):
        self.username, self.password = username, password
        self.sender = None
        self.receiver = None

    def __del__(self):
        if self.sender:
            logging.debug("Logging out SMTP")
            self.sender.quit()
            logging.info("SMTP logged out")
        if self.receiver:
            logging.debug("Logging out IMAP")
            self.receiver.logout()
            logging.info("IMAP logged out")

    def login(self):
        """Login everything for sending and receiving emails"""
        self.login_smtp()
        logging.info("SMTP logged in")
        self.login_imap()
        logging.info("IMAP logged in")

    def login_smtp(self):
        """login the SMTP client"""
        logging.debug("Logging in SMTP")
        self.sender = smtplib.SMTP('smtp.gmail.com:587')
        self.sender.ehlo()
        self.sender.starttls()
        self.sender.ehlo()
        self.sender.login(self.username, self.password)

    def login_imap(self):
        logging.debug("Logging in IMAP")
        self.receiver = imaplib.IMAP4_SSL('imap.gmail.com', 993)
        self.receiver.login(self.username, self.password)
        self.receiver.select()

    def send_email(self, to, subject, body):
        logging.nfo("Sending message to {0}".format(to))
        if type(to) != type([]):
            to = [to]
        message = self.message % (self.username, ", ".join(to), subject, body)
        self.sender.sendmail(self.username, to, message)
        logging.debug("Message sent")

    def send_intro_email(self):
        """docstring for send_intro_email"""
        message = """\
        Welcome to pyMote! This piece of software was built on the idea of
        simple remote "administration". You can use this to communicate with
        your computer from anywhere in the world, simply by sending an email
        to an address you have specified. """

        self.send_email(self.username, "Welcome to pyMote!", message)

    def receive_mail(self):
        """Retrieve all unread messages and return them as a list of Emails"""
        status, data = self.receiver.search(None, '(UNSEEN)')

        emails = []

        if status == 'OK' and len(data[0]) > 0:
            for datum in data[0].split(' '):
                result, msg_info = self.receiver.fetch(datum, 'RFC822')

                if result == 'OK':
                    msg = HeaderParser().parsestr(msg_info[0][1])

                    sender = msg['From']
                    receiver = msg['To']
                    subject = msg['Subject']

                    body = email.message_from_string(msg_info[0][1])

                    text = ''

                    #TODO: Add in the magic to add files
                    for part in body.walk():
                        if part.get_content_maintype() == 'multipart':
                            continue

                        if part.get_content_subtype() != 'plain':
                            continue

                        text = part.get_payload()

                    emails.append(Email(sender, receiver, subject, text))

        return emails


class MessageProcessThread(Thread):
    """Thread for processing a message and replying accordingly."""
    def __init__(self, message, sender):
        Thread.__init__(self)

        self.message = message
        self.sender = sender

    def run(self):
        """React accordingly."""
        for pattern in tuple(config['scripts'].keys()):
            if self.message.search(pattern):
                logging.info("executing" + config['scripts'][pattern])
                command = ["scripts/" + config['scripts'][pattern]]
                command.append(self.message.sender)
                command.append(self.message.receiver)
                command.append(self.message.subject)
                command.append(self.message.message)

                pipe = Popen(command, shell=True, bufsize=-1, stdout=PIPE, stderr=PIPE)

                pipe.wait()
                logging.debug("Popen for {0} complete".format(command))
                # stderr is the "script" or simple commands that will be interpreted, i.e. changing a setting.
                self.script = pipe.stderr
                # stdout is the output to send back to the sender.
                self.reply_message = pipe.stdout

                if not self.process_script():
                    self.process_message()

                #TODO react here.
                return

    def process_script(self):
        """docstring for process_script"""
        return False

    def process_message(self):
        """docstring for process_message"""
        to = self.message.sender
        subject = "RE: {0}".format(self.message.subject)
        body = self.reply_message
        sender.send_email(to, subject, body)


class ProcessThreadsStarter(Thread):
    """Thread for starting a MessageProcessThread for each email. Prevents the main program flow from becoming too blocked"""
    def __init__(self, server):
        Thread.__init__(self)
        self.server = server

    def run(self):
        self.messages = self.server.receive_mail()

        if len(self.messages) == 0:
            logging.info("No instructions were received!")
        for message in self.messages:
            msg_thread = MessageProcessThread(message)
            msg_thread.start()


def get_time():
    return int(time.strftime("%M"))


#TODO: This has to be fixed so it can't fuck itself to pieces from flooding the CPU each minute it goes on.
def calculate_refresh(refresh_time, refresh_time_checked=False):
    """Calculate how long until instructions should be checked"""
    try:
        return int(refresh_time) * 60
    except ValueError:
        start_char = refresh_time[:1]
        desired_time = int(refresh_time[1:])

        current_time = get_time()

        if start_char == ':':
            if not refresh_time_checked:
                logging.info("Checking at {0} past, on the hour".format(desired_time))
            if desired_time == current_time:
                return 0
            elif desired_time > current_time:
                return (desired_time - current_time) * 60
            else:
                return ((current_time - desired_time) + 60) * 60
        elif start_char == '/':
            if not refresh_time_checked:
                logging.info("Next check at {0} minutes, normalised".format(esired_time))

            if current_time % desired_time == 0:
                return desired_time * 60

            # make current_time divisible by 10.
            current_time = current_time % desired_time

            if desired_time > current_time:
                return (desired_time - current_time) * 60
            else:
                return current_time - desired_time + 60

        elif start_char == 's':
            if not refresh_time_checked:
                logging.info("Checking every {0} seconds".format(desired_time))
            return desired_time
        elif start_char == 'h':
            if not refresh_time_checked:
                logging.info("Checking every {0} hours".format(desired_time))
            return desired_time * 60 * 60
        else:
            return -1


def start():
    """Start the pymote system."""
    global_file = "/usr/share/pymote/pymoterc"
    user_file = os.path.normpath(os.environ['HOME'] + "/.pymoterc")
    config = get_config(user_file, global_file)
    log_file = 'pymote.log'
    log_format = "[%(asctime)s] %(levelname)s: %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    logging.basicConfig(filename=log_file, level=logging.DEBUG, format="[%(asctime)s] %(levelname)s: %(message)s", datefmt=date_format)
    refresh_time = config['settings']['refresh_time']
    username = config['settings']['username']
    password = config['settings']['password']
    signal.signal(signal.SIGSEGV, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    logging.info("Forking to background...")
    pid = 0 #os.fork()

    if pid != 0:
        logging.info("Closing main process.")
        sys.exit(0)

    server = EmailServer(username, password)
    server.login()
    #server.send_intro_email()
    try:
        calculate_refresh(refresh_time)
    except ValueError as e:
        logging.critical("refresh_time in your config file MUST be a number! Consult the documentation.")
        sys.exit(1)

    while True:
        new_refresh = calculate_refresh(refresh_time, True)
        logging.info("Checking instructions in {0} seconds, calculated from {1}".format(new_refresh, refresh_time))
        time.sleep(new_refresh)  # make this accept the more complex desired_times
        logging.info("Checking for new instructions")
        ProcessThreadsStarter(server).start()

try:
    start()
except KeyboardInterrupt:
    shutdown()
