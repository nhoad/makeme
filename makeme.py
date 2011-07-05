#!/usr/bin/env python
import os
import logging
import configparser
import sys
import time
import imaplib
import smtplib
import socket

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

    def search(self, pattern):
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
        """Return a list of Email objects"""
        if self.error:
            return None

        return []


class MakeMe(object):
    def __init__(self):
        """Initialise the MakeMe object. Sets _running to True, loads the config and logging, forking if requested."""
        self._running = True
        self._load_config()

        if self.config.getboolean('settings', 'fork'):
            pid = os.fork()

            if pid:
                sys.exit(0)

        self._start_logging()
        logging.info('Starting Makeme server')

        if not self.config.getboolean('settings', 'sent_welcome_message'):
            self._send_welcome_message()
            self.config.set('settings', 'sent_welcome_message', True)

            with open(self.local_config, 'w') as f:
                self.config.write(f)

    def _act(self, message):
        """Interpret and handle a message.

        Keyword arguments:
        message -- Email object to parse and handle.

        """
        logging.info('_act() not yet implemented')

    def _get_mailhandler(self):
        """Return a MailHandler object built from the config."""
        get = self.config.get
        getint = self.config.getint
        getboolean = self.config.getboolean
        username = get('settings', 'username')
        password = get('settings', 'password')
        smtp_server = get('settings', 'smtp_server')
        smtp_port = getint('settings', 'smtp_port')
        imap_server = get('settings', 'imap_server')
        imap_port = getint('settings', 'imap_port')
        use_tls = getboolean('settings', 'smtp_tls')
        use_ssl = getboolean('settings', 'imap_ssl')

        return MailHandler(username, password, smtp_server, smtp_port, imap_server, imap_port, use_ssl, use_tls)

    def _load_config(self):
        """Load global (/usr/share/makeme/makeme.conf) and user-level ($HOME/.makeme/makeme.conf) config files."""
        config = dict()

        global_config = '/usr/share/makeme/makeme.conf'
        local_config =self.local_config = os.path.join(os.environ['HOME'], '.makeme/makeme.conf')

        config['log_file'] = os.path.join(os.environ['HOME'], '.makeme/makeme.log')
        config['log_format'] = '[%(asctime)s] %(levelname)s: %(message)s'
        config['log_level'] = 'INFO'
        config['date_format'] = '%Y-%m-%d %H:%M:%S'
        config['smtp_server'] = 'smtp.gmail.com'
        config['smtp_port'] = 587
        config['smtp_tls'] = 'yes'
        config['imap_server'] = 'imap.gmail.com'
        config['imap_port'] = 993
        config['imap_ssl'] = 'yes'
        config['sent_welcome_message'] = 'no'
        config['fork'] = False
        config['refresh_time'] = 5

        self.config = configparser.RawConfigParser(config)

        if not self.config.read(global_config) and not self.config.read(local_config):
            print('No makeme.conf file could be found. Check the documentation for details.', file=sys.stderr)
            sys.exit(1)

    def _send_welcome_message(self):
        """Send the welcome message to username from config."""
        logging.info('_send_welcome_message() not written yet')

    def _start_logging(self):
        """Start logging to $HOME/.makeme/makeme.log."""
        c = self.config
        log_format = c.get('settings', 'log_format')
        date_format = c.get('settings', 'date_format')
        log_level = eval('logging.{}'.format(c.get('settings', 'log_level').upper()))
        log_file = c.get('settings', 'log_file')
        logging.basicConfig(filename=log_file, level=log_level, format=log_format, datefmt=date_format)

    def check_messages(self):
        """Check for messages and call _act() on each one."""
        logging.info('Checking messages...')

        messages = self._get_mailhandler().get_messages()

        if messages is None:
            self.stop()
            return

        if messages:
            logging.info('Received {} messages'.format(len(messages)))

        for m in messages:
            self._act(m)

    def running(self):
        """Return True if the server is running, false otherwise."""
        return self._running

    def shutdown(self):
        """Shutdown the server and all relevant connections."""
        logging.info('Shutting down Makeme')

    def stop(self):
        """Stop the server."""
        logging.info('Stopping Makeme')
        self._running = False

    def wait(self):
        """Sleep until the message queue should be checked."""
        time.sleep(self.config.getint('settings', 'refresh_time'))


class MakeMeCLI(MakeMe):
    def __init__(self):
        """Load the MakeMe server and parse command line arguments."""
        MakeMe.__init__(self)

        self._parse_argv()

    def _parse_argv(self):
        """Parse sys.argv for options, overloading those set in the config."""
        print('argv parsing not yet implemented.', file=sys.stderr)


try:
    if __name__ == '__main__':
        server = MakeMeCLI()
        running = server.running
        wait = server.wait
        check_messages = server.check_messages

        while running():
            check_messages()
            wait()

        server.shutdown()

except KeyboardInterrupt:
    server.shutdown()
except (configparser.NoSectionError, configparser.NoOptionError) as e:
    print('Makeme: Error processing your makeme.conf:', e, file=sys.stderr)
    server.shutdown()
    sys.exit(1)
