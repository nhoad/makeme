import os
class MakeMe(object):
    def __init__(self):
        """Initialise the MakeMe object. Sets _running to True, loads the
        config and logging, forking if requested.

        """
        self._running = True
        self._load_config()

        if self.config['fork']:
            pid = os.fork()

        if pid:
            sys.exit(0)

        print('I should set up logging now')

    def _load_config(self):
        raise NotImplementedError('config loading not yet implemented')

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
        raise NotImplementedError('argv parsing not yet implemented')

if __name__ == '__main__':
    server = MakeMeCLI()
    running = server.running
    wait = server.wait
    check_messages = server.check_messages

    while running():
        check_messages()
        wait()

    server.shutdown()
