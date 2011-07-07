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
import sys
import tempfile
import traceback

from smtplib import SMTPAuthenticationError
from email import encoders
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.parser import HeaderParser
from email.utils import formatdate


class Email(object):
    def __init__(self, sender=None, receiver=None, subject=None, body=None):
        """Initialise an Email object.

        Keyword arguments:
        sender -- address that sent the email
        receiver -- recipient of the email
        subject -- email's subject
        body -- body of the email

        """

        self.sender = sender if sender else receiver
        self.receiver = receiver
        self.subject = subject
        self.body = body
        self.files = []

    def attach_file(self, filename, filepath=None):
        """Attach a file to an Email.

        if filepath is None, then filename will be used as the name and path.

        Keyword arguments:

        filename -- name of the file as it will appear in the Email.
        filepath -- path to the file data.

        """
        if not filepath:
            filepath = filename

        self.files.append((filename, filepath))

    def __repr__(self):
        """Nice formatted output."""
        return 'Email(receiver={0}, sender={1}, subject={2}, body={3})'.format(self.receiver, self.sender, self.subject, self.body)

    def match(self, pattern):
        """Search the message and subject for pattern.

        Keyword arguments:
        pattern -- string/regex to search for.

        """
        p = r'%s'.lower() % pattern
        return re.search(p, self.subject.lower()) or re.search(p, self.body.lower())

class MailHandler(object):
    def __init__(self, username, password, smtp_server, smtp_port, imap_server, imap_port, use_ssl, use_tls):
        """Set the username, password, SMTP and IMAP info, and log in.

        Keyword arguments:
        username -- username to log into IMAP and SMTP
        password -- password to log into IMAP and SMTP
        smtp_server -- IP or hostname of SMTP server
        smtp_port -- port of SMTP server
        imap_server -- IP or hostname of IMAP server
        imap_port -- port of IMAP server
        use_ssl -- boolean for whether to use ssl or not to connect to IMAP
        use_tls -- boolean for whether to use tls or not to connect to SMTP

        """
        self.username = username
        self.password = password
        self.imap_details = (imap_server, imap_port, use_ssl)
        self.smtp_details = (smtp_server, smtp_port, use_tls)
        self.error = False
        self.imap = self.smtp = None

        try:
            self._login_imap()
            self._login_smtp()
        except (imaplib.IMAP4.error, socket.gaierror) as e:
            self.error = True
            logging.critical('IMAP error: ' + str(e))
        except smtplib.SMTPAuthenticationError as e:
            self.error = True
            logging.critical('SMTP error: ' + str(e))

    def __del__(self):
        """Clean up resources. Logs out IMAP and SMTP clients."""
        if self.imap:
            logging.debug('Logging out IMAP')
            self.imap.logout()
            logging.debug('IMAP logged out')

        if self.smtp:
            logging.debug('Logging out SMTP')
            self.smtp.quit()
            logging.debug('SMTP logged out')

    def _login_imap(self):
        """Log in to the IMAP server. Set self.imap to the connection object."""
        logging.debug('Logging in IMAP')

        server, port, secure = self.imap_details

        self.imap = imaplib.IMAP4_SSL(server, port) if secure else imaplib.IMAP4(server, port)
        self.imap.login(self.username, self.password)
        self.imap.select()

        logging.debug('IMAP logged in')

    def _login_smtp(self):
        """Log in to the SMTP server. Set self.smtp to the connection object."""
        logging.debug('Logging in SMTP')

        server, port, secure = self.smtp_details

        self.smtp = smtplib.SMTP(server, port)
        self.smtp.ehlo()

        if secure:
            self.smtp.starttls()

        self.smtp.ehlo()
        self.smtp.login(self.username, self.password)

        logging.debug('SMTP logged in')

    def get_messages(self):
        """Return a list of Email objects."""

        if self.error:
            return None

        emails = []

        imap = self.imap
        status, data = imap.search(None, '(UNSEEN)')

        logging.debug('Status from UNSEEN: {}'.format(status))
        logging.debug('Data from UNSEEN: {}'.format(data))

        if status == 'OK' and len(data[0]) > 0:
            logging.debug('There are new emails!')
            split_data = str(data[0], encoding='utf8').split(' ')
            logging.debug('Split data from UNSEEN: {}'.format(split_data))

            for datum in split_data:
                status, msg_info = self.imap.fetch(datum, 'RFC822')

                if status == 'OK':
                    msg = HeaderParser().parsestr(str(msg_info[0][1], encoding='utf8'))

                    sender = msg['From']
                    receiver = msg['To']
                    subject = msg['Subject']

                    body = email.message_from_string(str(msg_info[0][1], encoding='utf8'))

                    text = ''

                    e = Email(sender=sender, receiver=receiver, subject=subject)

                    for part in body.walk():
                        if part.get_content_maintype() == 'multipart':
                            continue

                        if part.get_content_subtype() != 'plain':
                            continue

                        if part.get('Content-Disposition') is None:
                            e.body = part.get_payload()
                            continue

                        # if we end up down here, it's a file attachment

                        filename = part.get_filename()
                        filepath = tempfile.mkstemp()[1]

                        with open(filepath, 'wb') as f:
                            f.write(part.get_payload(decode=True))

                        e.attach_file(filename, filepath)

                    emails.append(e)

        return emails

    def send_email(self, email):
        """Send an email.

        Keyword arguments:
        email -- Email object to send

        """
        logging.info('Sending message to {}'.format(email.receiver))

        if isinstance(email.receiver, list):
            to = [email.receiver]

        msg = MIMEMultipart()
        msg['From'] = email.sender
        msg['To'] = ', '.join(to)
        msg['Date'] = formatdate(localtime=True)
        msg['Subject'] = email.subject

        msg.attach(MIMEText(email.body))

        if len(email.files) > 0:
            for name, path in email.files:
                data = open(name, 'rb').read()
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(data)
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', 'attachment; filename="{}"'.format(os.path.basename(name)))

                msg.attach(part)

        self.smtp.sendmail(self.username, to, msg.as_string())
        logging.debug('Message sent')

