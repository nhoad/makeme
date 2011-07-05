import os
class MakeMe(dict):
    def __init__(self):
        dict.__init__(self)

        self._running = True
        #self._load_config()

        if self['fork']:
            pid = os.fork()

        if pid:
            sys.exit(0)

        print('I should set up logging now')

    def _load_config(self):
        raise NotImplementedError('config loading not yet implemented')

    def check_messages(self):
        raise NotImplementedError('check_messages not yet implemented')

    def running(self):
        return self._running

    def shutdown(self):
        raise NotImplementedError('server does not shutdown properly yet')

    def stop(self):
        self._running = False

    def wait(self):
        raise NotImplementedError('wait not yet implemented')


class MakeMeCLI(MakeMe):
    def __init__(self):
        MakeMe.__init__(self)

        self._parse_argv()

    def _parse_argv(self):
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
