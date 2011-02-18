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
import os
import tempfile

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
        self.files = []

    def attach_file(self, filename, filepath=None):
        """Attach a file to the email object

        if filepath is None, then filename will be used as the name as well as the path to the data.

        Keyword arguments:
        filename -- name of the file.
        filepath -- path to the file data, typically in a temporary directory.

        """
        self.files.append((filename, filepath))

    def __str__(self):
        return 'Email <receiver={0}, sender={1}, subject={2}, body={3}>'.format(self.receiver, self.sender, self.subject, self.body)

    def search(self, pattern):
        """Search the message and subject for pattern, return true or false

        Keyword arguments:
        pattern -- the string to search for, can also be a regular expression

        """
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
        self.smtp_server = 'smtp.gmail.com'
        self.smtp_port = 587
        self.imap_server = 'imap.gmail.com'
        self.imap_port = 993
        self.imap_use_ssl = True
        self.smtp_use_tls = True
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
        """Change particular stored values and update them accordingly

        Keyword arguments:
        username -- the new username to change to (for imap and smtp)
        password -- the new password to change to (for imap and smtp)
        contact_address -- the new address to be contacted for on crashes or info messages
        patterns -- the new patterns to check new messages against
        refresh_time -- the new refresh time, how often to check for messages

        """
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

    def set_imap(self, imap_server, imap_port, use_ssl):
        """set the IMAP server settings.

        Keyword arguments:
        imap_server -- IP address or domain to connect to.
        imap_port -- port to connect through.
        use_ssl -- should the connection be secure?

        """
        self.imap_server = imap_server
        self.imap_port = imap_port
        self.imap_use_ssl = use_ssl
        self.smtp_use_tls = True

    def set_smtp(self, smtp_server, smtp_port, use_tls):
        """set the IMAP server settings.

        Keyword arguments:
        smtp_server -- IP address or domain to connect to.
        smtp_port -- port to connect through.
        use_tls -- should the connection be secure?

        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.smtp_use_tls = use_tls

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

    def login_smtp(self):
        """login the SMTP client"""
        logging.debug("Logging in SMTP")
        try:
            self.sender = smtplib.SMTP(self.smtp_server, self.smtp_port)
            self.sender.ehlo()
            if self.smtp_use_tls:
                self.sender.starttls()
            self.sender.ehlo()
            self.sender.login(self.username, self.password)
            logging.info("SMTP logged in")
        except SMTPAuthenticationError as e:
            message = "Error logging into SMTP: {0}".format(e)
            logging.critical(message)
            print(message)
            raise ShutdownException(2)

    def login_imap(self):
        """log in the IMAP client"""
        logging.debug("Logging in IMAP")
        try:
            if self.receiver is not None:
                self.receiver.logout()

            if self.imap_use_ssl:
                self.receiver = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            else:
                self.receiver = imaplib.IMAP4(self.imap_server, self.imap_port)

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
            data = open(email.filename, 'rb').read()
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(data)
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', 'attachment; filename="{0}"'.format(os.path.basename(email.filename)))

            msg.attach(part)

        self.sender.sendmail(self.username, to, msg.as_string())
        logging.debug("Message sent")

    def send_intro_email(self):
        """Send the introductory email to the specified contact address"""

        f = open(os.path.join(os.getcwd(), "/messages/intro", 'r'))
        message = ''.join(f.readlines())
        f.close()

        if self.contact_address is None:
            logging.info("Inntroductory email can't be sent. No contact address specified.")

        self.send_email(Email(sender=self.username, receiver=self.contact_address, subject="Welcome to makeme!", body=message))

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

                    e = Email(sender=sender, receiver=receiver, subject=subject)

                    #TODO: Add in the magic to add files
                    for part in body.walk():
                        if part.get_content_maintype() == 'multipart':
                            continue

                        if part.get_content_subtype() != 'plain':
                            continue

                        if part.get('Content-Disposition') is None:
                            e.body = part.get_payload()
                            continue

                        # not sure why I did this, I seem to get the body up the top too.

                        filename = part.get_filename()

                        filepath = tempfile.mkstemp()[1]
                        fp = open(filepath, 'wb')
                        fp.write(part.get_payload(decode=True))
                        fp.close()

                        e.attach_file(filename, filepath)

                    print(e)
                    emails.append(e)
        else:
            logging.debug("There are NO new emails!")

        return emails

    def check_messages(self):
        """Login via IMAP and create a ProcessThreadStarter for processing."""
        self.login_imap()
        threads.ProcessThreadsStarter(self, self.patterns).start()

    def add_email_to_queue(self,email):
        """Add an email to the queue, to be sent when SMTP reconnects.

        Keyword Arguments:
        email -- the Email object to add to the queue.

        """
        self.unsent_emails.append(email)

    def run(self, refresh_time):
        """Run the server.

        Keyword Arguments:
        refresh_time -- the refresh time read from the config file. Should be a string.

        """

        functions.calculate_refresh(refresh_time)
        self.refresh_time = refresh_time

        while True:
            self.lock.acquire()
            refresh_time = self.refresh_time
            self.lock.release()

            new_refresh = functions.calculate_refresh(refresh_time, True)
            logging.info("Checking instructions in {0} seconds, calculated from {1}".format(new_refresh, refresh_time))
            time.sleep(new_refresh)
            logging.info("Checking for new instructions")
            self.check_messages()
