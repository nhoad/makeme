'''
File: emails.py
Author: Nathan Hoad
Description: Holds email handling classes
'''

import logging
import email
import smtplib
import imaplib
import re
import time

from smtplib import SMTPAuthenticationError
from email import encoders
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.parser import HeaderParser
from email.utils import formatdate

from exceptions import ShutdownException
import threads
import functions

from threading import Lock


class Email():
    """email wrapper class to make handling emails nicer"""
    def __init__(self, sender=None, receiver=None, subject=None, body=None):
        """ Initialise Email class.

        Keyword arguments:
        sender -- address that sent the email
        receiver -- address that received the email
        subject -- the subject of the email
        body -- the body of the email

        """
        if not sender:
            self.sender = receiver
        else:
            self.sender = sender

        self.receiver = receiver
        self.subject = subject
        self.body = body
        self.filename = None

    #TODO complete this
    def attach_file(self, filename, data):
        """Attach a file to the email object

        Keyword arguments:
        filename -- the name of the file, with NO PATH. Filename ONLY.
        data -- binary data of the file.

        """
        self.filename = filename
        self.data = data

    def search(self, pattern):
        """Search the message and subject for pattern, return true or false"""
        return re.search(r'%s'.lower() % pattern, self.subject.lower()) or re.search(r'%s'.lower() % pattern, self.body.lower())


class EmailServer():
    """EmailServer wraps up all email processing using Email where possible."""

    def __init__(self, username, password):
        """Initialise the email server.

        Keyword arguments:
        username -- username to log into the SMTP and IMAP servers.
        password -- password to log into the SMTP and IMAP servers.

        """
        self.message = """From: %s\r\nTo: %s\r\nSubject: %s\r\n%s\r\n"""
        self.username, self.password = username, password
        self.sender = None
        self.receiver = None
        self.unsent_emails = []
        self.contact_address = None
        self.lock = Lock()

    def __del__(self):
        """Clean up the EmailServer. Logs things out and whatnot."""
        if self.sender:
            logging.debug("Logging out SMTP")
            self.sender.quit()
            logging.info("SMTP logged out")
        if self.receiver:
            self.logout_imap()

    def reload_values(self, username, password, contact_address, patterns, refresh_time):
        logging.info("Config file was changed, reloading...")
        self.lock.acquire()
        if self.password != password or self.username != username:
            self.password = password
            self.username = username

            self.sender.quit()
            self.login_smtp()

        self.contact_address = contact_address
        self.patterns = patterns
        self.refresh_time = refresh_time

        self.lock.release()

    def logout_imap(self):
        """Logout the IMAP account. Keeps things tidy."""
        logging.debug("Logging out IMAP")
        # really bad, but no other way to handle bad file descritor
        try:
            self.receiver.logout()
        except Exception:
            pass
        logging.info("IMAP logged out")
        self.receiver = None

    #TODO make it able to connect to more than Gmail
    def login_smtp(self):
        """login the SMTP client"""
        logging.debug("Logging in SMTP")
        try:
            self.sender = smtplib.SMTP('smtp.gmail.com:587')
            self.sender.ehlo()
            self.sender.starttls()
            self.sender.ehlo()
            self.sender.login(self.username, self.password)
            logging.info("SMTP logged in")
        except SMTPAuthenticationError as e:
            message = "Error logging into SMTP: {0}".format(e)
            logging.critical(message)
            print(message)
            raise ShutdownException(2)

    #TODO make it able to connect to more than Gmail
    def login_imap(self):
        """log in the IMAP client"""
        logging.debug("Logging in IMAP")
        try:
            if self.receiver is not None:
                self.receiver.logout()

            self.receiver = imaplib.IMAP4_SSL('imap.gmail.com', 993)
            self.receiver.login(self.username, self.password)
            self.receiver.select()
        except Exception as e:
            logging.critical("Error logging into IMAP: {0}".format(e))
            raise ShutdownException(3)

    def send_email(self, email):
        """Send an email via the SMTP account.

        Keyword arguments:
        email -- Email object to send.

        """
        logging.info("Sending message to {0}".format(email.receiver))

        if type(email.receiver) != type([]):
            to = [email.receiver]

        msg = MIMEMultipart()
        msg['From'] = email.sender
        msg['To'] = ', '.join(to)
        msg['Date'] = formatdate(localtime=True)
        msg['Subject'] = email.subject

        msg.attach(MIMEText(email.body))

        if email.filename:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(email.data)
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', 'attachment; filename="{0}"'.format(email.filename))

            msg.attach(part)

        self.sender.sendmail(self.username, to, msg.as_string())
        logging.debug("Message sent")

    def send_intro_email(self):
        """docstring for send_intro_email"""
        message = """\
        Welcome to makeme! This piece of software was built on the idea of
        simple remote "administration". You can use this to communicate with
        your computer from anywhere in the world, simply by sending an email
        to an address you have specified. """

        if self.contact_address is None:
            logging.info("Inntroductory email can't be sent. No contact address specified.")

        self.send_email(Email(self.contact_address, "Welcome to makeme!", message))

    def receive_mail(self):
        """Retrieve all unread messages and return them as a list of Emails"""
        status, data = self.receiver.search(None, '(UNSEEN)')

        emails = []

        logging.debug("Status from (UNSEEN): {0}".format(status))
        logging.debug("Data from (UNSEEN): {0}".format(data))

        if status == 'OK' and len(data[0]) > 0:
            logging.debug("There are new emails!")
            split_data = str(data[0], encoding='utf8').split(' ')
            logging.debug("Split_data from (UNSEEN): {0}".format(split_data))
            for datum in split_data:
                result, msg_info = self.receiver.fetch(datum, 'RFC822')

                if result == 'OK':
                    msg = HeaderParser().parsestr(str(msg_info[0][1], \
                        encoding='utf8'))

                    sender = msg['From']
                    receiver = msg['To']
                    subject = msg['Subject']

                    body = email.message_from_string(str(msg_info[0][1], \
                        encoding='utf8'))

                    text = ''

                    #TODO: Add in the magic to add files
                    for part in body.walk():
                        if part.get_content_maintype() == 'multipart':
                            continue

                        if part.get_content_subtype() != 'plain':
                            continue

                        text = part.get_payload()

                    emails.append(Email(sender=sender, receiver=receiver, subject=subject, body=text))
        else:
            logging.debug("There are NO new emails!")

        return emails

    def check_messages(self):
        """Login via IMAP and create a ProcessThreadStarter for processing."""
        self.login_imap()
        threads.ProcessThreadsStarter(self, self.patterns).start()

    def add_email_to_queue(self,email):
        self.unsent_emails.append(email)

    def run(self, refresh_time):
        """docstring for run"""

        self.refresh_time = functions.calculate_refresh(refresh_time)

        while True:
            self.lock.acquire()
            refresh_time = self.refresh_time
            self.lock.release()

            new_refresh = functions.calculate_refresh(refresh_time, True)
            logging.info("Checking instructions in {0} seconds, calculated from {1}".format(new_refresh, refresh_time))
            time.sleep(new_refresh)
            logging.info("Checking for new instructions")
            self.check_messages()
