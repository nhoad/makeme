def MakeMe(object):
    def __init__(self):
        self._running = True
        self._parse_argv()
        self._load_config()

    def _parse_argv(self):
        raise NotImplementedError('argv parsing not yet implemented')

    def _load_config(self):
        raise NotImplementedError('config loading not yet implemented')

    def running(self):
        return self._running

    def wait(self):
        raise NotImplementedError('wait not yet implemented')

    def check_messages(self):
        raise NotImplementedError('check_messages not yet implemented')
