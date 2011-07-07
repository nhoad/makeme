#!/usr/bin/env python

from threading import Thread

class MessageProcessor(Thread):
    def __init__(self, email_client, action):
        """Initialise MessageProcessor and store email_client and action.

        Keyword arguments:
        email_client -- factory function to create a MailHandler object.
        action -- function to be called on each message.

        """
        Thread.__init__(self)

        self.email_client = email_client
        self.action = action

    def run(self):
        """Check for emails using self.email_client and call self.action on each one."""
        e = self.email_client()

        messages = e.get_messages()

        for m in messages:
            self.action(m)
