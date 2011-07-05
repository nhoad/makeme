#!/usr/bin/env python
import os
import logging
import configparser
import sys

class MakeMe(object):
    def __init__(self):
        """Initialise the MakeMe object. Sets _running to True, loads the config and logging, forking if requested."""
        self._running = True
        self._load_config()

        if self.config.get('settings', 'fork'):
            pid = os.fork()

            if pid:
                sys.exit(0)

        self._start_logging()

    def _load_config(self):
        """Load global (/usr/share/makeme/makeme.conf) and user-level ($HOME/.makeme/makeme.conf) config files."""
        config = dict()

        global_config = '/usr/share/makeme/makeme.conf'
        local_config = os.path.join(os.environ['HOME'], '.makeme/makeme.conf')

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

        self.config = configparser.RawConfigParser(config)
        
        if not self.config.read(global_config) and not self.config.read(local_config):
            print('No makeme.conf file could be found. Check the documentation for details.', file=sys.stderr)
            sys.exit(1)

    def _start_logging(self):
        """Start logging to $HOME/.makeme/makeme.log."""
        c = self.config
        log_format = c.get('settings', 'log_format')
        date_format = c.get('settings', 'date_format')
        log_level = eval('logging.{}'.format(c.get('settings', 'log_level').upper()))
        log_file = c.get('settings', 'log_file')
        logging.basicConfig(filename=log_file, level=log_level, format=log_format, datefmt=date_format)
        logging.info('')

    def check_messages(self):
        raise NotImplementedError('check_messages not yet implemented')

    def running(self):
        """Return True if the server is running, false otherwise."""
        return self._running

    def shutdown(self):
        raise NotImplementedError('server does not shutdown properly yet')

    def stop(self):
        """Stop the server."""
        self._running = False

    def wait(self):
        """Sleep until the message queue should be checked."""
        raise NotImplementedError('wait not yet implemented')


class MakeMeCLI(MakeMe):
    def __init__(self):
        """Load the MakeMe server and parse command line arguments."""
        MakeMe.__init__(self)

        self._parse_argv()

    def _parse_argv(self):
        """Parse sys.argv for options, overloading those set in the config."""
        print('argv parsing not yet implemented', file=sys.stderr)

if __name__ == '__main__':
    server = MakeMeCLI()
    running = server.running
    wait = server.wait
    check_messages = server.check_messages

    while running():
        check_messages()
        wait()

    server.shutdown()
